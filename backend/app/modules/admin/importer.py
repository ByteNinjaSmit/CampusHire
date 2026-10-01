"""Bulk import of students and companies from CSV / XLSX.

``run_import_job(job_id)`` is called by the Celery task ``data.import`` through ``runtime.run_async``.
The uploaded file lives in the ``documents`` bucket (``documents`` row kind IMPORT, referenced by
``job.params.document_id``). Every row is validated with the same field types the API uses
(``core.validators`` via ``users.schemas``), then inserted in its own SAVEPOINT so one bad row never blocks the
rest. Imported students get a random temporary password and an emailed password-reset link.

Result stored on the job: ``{rows_ok, rows_failed, errors: [{row, field, message}], total_rows, entity}``;
``row`` is the 1-based spreadsheet row number (header = row 1).
"""

import csv
import io
import logging
import re
import secrets
import uuid
from datetime import date, datetime
from typing import Annotated, Any

from openpyxl import Workbook, load_workbook
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import side_effects
from app.core.base import utcnow
from app.core.errors import map_integrity_error
from app.core.security import hash_password
from app.core.storage import Storage
from app.core.storage import storage as default_storage
from app.core.types import Gpa
from app.core.validators import normalize_registration_number
from app.modules.admin import repository as repo
from app.modules.admin.exporter import _fail, _publish
from app.modules.admin.models import Job
from app.modules.auth.emails import send_reset_email
from app.modules.companies.models import Company
from app.modules.students.models import Student
from app.modules.users import schemas as us
from app.modules.users.models import User

log = logging.getLogger(__name__)

MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_ROWS = 5000
MAX_REPORTED_ERRORS = 200
ALLOWED_EXTENSIONS = (".csv", ".xlsx")


# ---- row schemas -------------------------------------------------------------------------------------------------
class StudentRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: us.Email
    full_name: us.FullName
    phone: us.Phone | None = None
    department: us.Department
    gpa: Gpa
    enrollment_no: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)] | None = None
    graduation_year: Annotated[int, Field(ge=2000, le=2100)] | None = None


class CompanyRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=160)]
    registration_number: Annotated[str, AfterValidator(normalize_registration_number)]
    location: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    contact_person_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
    contact_email: us.Email
    contact_phone: us.Phone | None = None
    industry: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = None
    website: us.Url | None = None
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)] | None = None


ROW_MODELS: dict[str, type[BaseModel]] = {"students": StudentRow, "companies": CompanyRow}
REQUIRED: dict[str, list[str]] = {
    "students": ["email", "full_name", "department", "gpa"],
    "companies": ["name", "registration_number", "location", "contact_person_name", "contact_email"],
}
COLUMNS: dict[str, list[str]] = {
    "students": ["email", "full_name", "phone", "department", "gpa", "enrollment_no", "graduation_year"],
    "companies": [
        "name",
        "registration_number",
        "location",
        "contact_person_name",
        "contact_email",
        "contact_phone",
        "industry",
        "website",
        "description",
    ],
}
SAMPLE: dict[str, list[Any]] = {
    "students": ["jane.doe@example.com", "Jane Doe", "+919876543210", "CSE", 3.5, "ENR-0001", 2027],
    "companies": [
        "Acme Labs",
        "U72200KA2015PTC082345",
        "Bengaluru, India",
        "John Smith",
        "hr@acme.example",
        "+919812345678",
        "Software",
        "https://acme.example",
        "Product engineering company",
    ],
}


def build_template(entity: str) -> bytes:
    """XLSX with the header row (required columns first) and one example row."""
    wb = Workbook()
    ws = wb.active
    ws.title = entity
    ws.append(COLUMNS[entity])
    ws.append(SAMPLE[entity])
    notes = wb.create_sheet("notes")
    notes.append(["column", "required"])
    for col in COLUMNS[entity]:
        notes.append([col, "yes" if col in REQUIRED[entity] else "no"])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


# ---- parsing --------------------------------------------------------------------------------------------------------
class ImportFileError(ValueError):
    """The file as a whole is unusable (bad format / missing columns / too large)."""


def _norm_header(h: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(h or "").strip().lower()).strip("_")


def _cell(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else repr(v)
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    text = str(v).strip()
    return text or None


def parse_rows(filename: str, data: bytes) -> tuple[list[str], list[tuple[int, dict[str, str | None]]]]:
    """Return ``(headers, [(row_number, {header: value})])``; blank rows are skipped."""
    name = filename.lower()
    raw_rows: list[list[Any]]
    if name.endswith(".xlsx"):
        try:
            wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            ws = wb.worksheets[0]
            raw_rows = [list(r) for r in ws.iter_rows(values_only=True)]
            wb.close()
        except Exception as exc:  # noqa: BLE001 - openpyxl raises many types for corrupt files
            raise ImportFileError("The file is not a valid .xlsx workbook") from exc
    elif name.endswith(".csv"):
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ImportFileError("CSV files must be UTF-8 encoded") from exc
        raw_rows = [list(r) for r in csv.reader(io.StringIO(text))]
    else:
        raise ImportFileError("Only .csv and .xlsx files are supported")
    if not raw_rows:
        raise ImportFileError("The file is empty")
    headers = [_norm_header(h) for h in raw_rows[0]]
    rows: list[tuple[int, dict[str, str | None]]] = []
    for idx, raw in enumerate(raw_rows[1:], start=2):
        values = {h: _cell(raw[i]) if i < len(raw) else None for i, h in enumerate(headers) if h}
        if not any(values.values()):
            continue
        rows.append((idx, values))
        if len(rows) > MAX_IMPORT_ROWS:
            raise ImportFileError(f"Too many rows (maximum {MAX_IMPORT_ROWS})")
    return headers, rows


def _friendly(err: dict[str, Any]) -> tuple[str, str]:
    field = ".".join(str(p) for p in err.get("loc", ())) or "row"
    msg = str(err.get("msg", "Invalid value"))
    if msg.startswith("Value error, "):
        msg = msg[len("Value error, ") :]
    if err.get("type") == "missing":
        msg = "This field is required"
    return field, msg


def validate_rows(
    entity: str, rows: list[tuple[int, dict[str, str | None]]]
) -> tuple[list[tuple[int, Any]], list[dict[str, Any]]]:
    model = ROW_MODELS[entity]
    valid: list[tuple[int, Any]] = []
    errors: list[dict[str, Any]] = []
    for number, values in rows:
        payload = {k: v for k, v in values.items() if v is not None}
        try:
            valid.append((number, model.model_validate(payload)))
        except ValidationError as exc:
            for err in exc.errors():
                field, msg = _friendly(dict(err))
                errors.append({"row": number, "field": field, "message": msg})
    return valid, errors


# ---- persistence ------------------------------------------------------------------------------------------------------
def _temp_password() -> str:
    # Random, and guaranteed to satisfy the password policy.
    return secrets.token_urlsafe(18) + "aA1!"


async def _existing(session: AsyncSession, column: Any, values: list[str]) -> set[str]:
    if not values:
        return set()
    res = await session.execute(select(column).where(column.in_(values)))
    return {str(v).lower() for v in res.scalars().all() if v is not None}


def _duplicate_errors(
    entity: str,
    valid: list[tuple[int, Any]],
    existing_keys: dict[str, set[str]],
) -> tuple[list[tuple[int, Any]], list[dict[str, Any]]]:
    unique_fields = {"students": ("email", "enrollment_no"), "companies": ("registration_number",)}[entity]
    seen: dict[str, dict[str, int]] = {f: {} for f in unique_fields}
    keep: list[tuple[int, Any]] = []
    errors: list[dict[str, Any]] = []
    for number, obj in valid:
        clash = False
        for f in unique_fields:
            value = getattr(obj, f)
            if value is None:
                continue
            key = str(value).lower()
            if key in existing_keys.get(f, set()):
                errors.append({"row": number, "field": f, "message": f"{f} already exists"})
                clash = True
            elif key in seen[f]:
                errors.append(
                    {"row": number, "field": f, "message": f"Duplicate {f} in file (first seen on row {seen[f][key]})"}
                )
                clash = True
            else:
                seen[f][key] = number
        if not clash:
            keep.append((number, obj))
    return keep, errors


async def _insert_student(session: AsyncSession, row: StudentRow) -> None:
    user = User(
        id=uuid.uuid4(),
        email=row.email,
        password_hash=hash_password(_temp_password()),
        role="STUDENT",
        full_name=row.full_name,
        phone=row.phone,
        email_verified_at=utcnow(),
    )
    session.add(user)
    await session.flush()
    session.add(
        Student(
            user_id=user.id,
            department=row.department,
            gpa=row.gpa,
            enrollment_no=row.enrollment_no,
            graduation_year=row.graduation_year,
            skills=[],
        )
    )
    await session.flush()
    await send_reset_email(session, user)  # temporary password + emailed reset link


async def _insert_company(session: AsyncSession, row: CompanyRow, actor_id: uuid.UUID | None) -> None:
    session.add(
        Company(
            id=uuid.uuid4(),
            name=row.name,
            registration_number=row.registration_number,
            location=row.location,
            contact_person_name=row.contact_person_name,
            contact_email=row.contact_email,
            contact_phone=row.contact_phone,
            industry=row.industry,
            website=row.website,
            description=row.description,
            status="ACTIVE",
            created_by=actor_id,
        )
    )
    await session.flush()


async def import_rows(session: AsyncSession, entity: str, job: Job, filename: str, data: bytes) -> dict[str, Any]:
    """Parse + validate + insert. Returns the job ``result`` dict. Raises ``ImportFileError`` for bad files."""
    headers, rows = parse_rows(filename, data)
    missing = [c for c in REQUIRED[entity] if c not in headers]
    if missing:
        raise ImportFileError(f"Missing required column(s): {', '.join(missing)}")

    valid, errors = validate_rows(entity, rows)
    job.progress = 30
    await session.commit()

    if entity == "students":
        existing = {
            "email": await _existing(session, User.email, [str(o.email) for _, o in valid]),
            "enrollment_no": await _existing(
                session, Student.enrollment_no, [o.enrollment_no for _, o in valid if o.enrollment_no]
            ),
        }
    else:
        existing = {
            "registration_number": await _existing(
                session, Company.registration_number, [o.registration_number for _, o in valid]
            )
        }
    valid, dup_errors = _duplicate_errors(entity, valid, existing)
    errors.extend(dup_errors)

    ok = 0
    total = max(len(valid), 1)
    for i, (number, obj) in enumerate(valid, start=1):
        try:
            async with session.begin_nested():
                if entity == "students":
                    await _insert_student(session, obj)
                else:
                    await _insert_company(session, obj, job.requested_by)
            ok += 1
        except IntegrityError as exc:
            errors.append({"row": number, "field": "row", "message": map_integrity_error(exc).message})
        if i % 50 == 0:
            job.progress = 30 + int(65 * i / total)
            await session.commit()
            await side_effects.flush(session)

    errors.sort(key=lambda e: (e["row"], e["field"]))
    result: dict[str, Any] = {
        "entity": entity,
        "total_rows": len(rows),
        "rows_ok": ok,
        "rows_failed": len({e["row"] for e in errors}),
        "errors": errors[:MAX_REPORTED_ERRORS],
    }
    if len(errors) > MAX_REPORTED_ERRORS:
        result["errors_truncated"] = True
    return result


async def run_import_job(
    job_id: uuid.UUID | str,
    *,
    session_factory: repo.SessionFactory | None = None,
    store: Storage | None = None,
) -> None:
    """Execute a DATA_IMPORT job end to end. Never raises: failures are recorded on the job."""
    job_id = uuid.UUID(str(job_id))
    store = store or default_storage
    async with repo.worker_session(session_factory) as session:
        job = await repo.get_job(session, job_id)
        if job is None:
            log.error("import job %s not found", job_id)
            return
        try:
            params = job.params or {}
            entity = str(params.get("entity", ""))
            if entity not in ROW_MODELS:
                raise ValueError(f"Unsupported import entity {entity!r}")
            doc = await repo.get_document(session, uuid.UUID(str(params.get("document_id"))))
            if doc is None:
                raise ValueError("Uploaded file not found")
            job.status = "RUNNING"
            job.started_at = utcnow()
            job.progress = 5
            await session.commit()

            data = await store.get_object(doc.bucket, doc.object_key)
            try:
                result = await import_rows(session, entity, job, doc.filename, data)
            except ImportFileError as exc:
                await _fail(session, job_id, str(exc))
                return

            job = await repo.get_job(session, job_id)
            assert job is not None
            job.result = result
            job.status = "SUCCEEDED"
            job.progress = 100
            job.finished_at = utcnow()
            if job.requested_by is not None:
                side_effects.notify(
                    session,
                    job.requested_by,
                    "SYSTEM",
                    "Import finished",
                    f"Imported {result['rows_ok']} {entity}; {result['rows_failed']} row(s) had errors.",
                    link="/admin/data",
                    data={"job_id": str(job.id)},
                )
                side_effects.audit(
                    session,
                    job.requested_by,
                    "data.import.complete",
                    "job",
                    job.id,
                    after={"entity": entity, "rows_ok": result["rows_ok"], "rows_failed": result["rows_failed"]},
                )
            await session.commit()
            await side_effects.flush(session)
            await _publish(job)
        except Exception as exc:  # noqa: BLE001
            log.exception("import job %s failed", job_id)
            await _fail(session, job_id, str(exc) or type(exc).__name__)
