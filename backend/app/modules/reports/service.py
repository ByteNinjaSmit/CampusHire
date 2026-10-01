"""Reports service: registry access, JSON reports, async export jobs and the worker entry point.

``run_export_job(job_id)`` is called by the Celery task ``reports.export`` (WP4a) through ``runtime.run_async``;
it opens its own NullPool engine so it never touches the API's engine or event loop (plan 1.3).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

import anyio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core import side_effects
from app.core.base import utcnow
from app.core.config import settings
from app.core.errors import forbidden, not_found, unprocessable
from app.core.pagination import PageParams, make_page, paginate
from app.core.storage import Storage, get_storage
from app.modules.admin.models import Job
from app.modules.documents.models import Document
from app.modules.reports.builders import REPORTS, ReportDef
from app.modules.reports.builders.common import parse_params
from app.modules.reports.renderers.pdf import render_pdf
from app.modules.reports.renderers.xlsx import render_xlsx
from app.modules.reports.schemas import ExportParams, JobOut, ReportData, ReportMeta
from app.modules.users.models import User

log = logging.getLogger(__name__)

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
STUDENT_KEYS = {"my-applications", "interview-schedule", "placement-status"}


# --------------------------------------------------------------------------- registry / access
def get_definition(key: str) -> ReportDef:
    d = REPORTS.get(key)
    if d is None:
        raise not_found("Unknown report")
    return d


def get_authorized_definition(user: User, key: str) -> ReportDef:
    d = get_definition(key)
    if user.role not in d.roles:
        raise forbidden()
    return d


def list_reports(user: User) -> list[ReportMeta]:
    return [d.meta for d in REPORTS.values() if user.role in d.listed_for]


async def build_report(session: AsyncSession, user: User, key: str, params: dict[str, Any]) -> ReportData:
    d = get_authorized_definition(user, key)
    return await d.builder(session, user, params)


# --------------------------------------------------------------------------- jobs
def report_link(user: User, key: str) -> str:
    if user.role == "ADMIN":
        return f"/admin/reports/{key}"
    return f"/{user.role.lower()}/reports"


def job_out(job: Job, download_url: str | None = None) -> JobOut:
    return JobOut(
        id=job.id,
        type=job.type,  # type: ignore[arg-type]
        status=job.status,  # type: ignore[arg-type]
        progress=job.progress or 0,
        params=job.params or {},
        result=job.result,
        error=job.error,
        download_url=download_url,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


async def download_url_for(session: AsyncSession, job: Job, store: Storage) -> str | None:
    if job.status != "SUCCEEDED" or job.result_document_id is None:
        return None
    doc = (await session.execute(select(Document).where(Document.id == job.result_document_id))).scalar_one_or_none()
    if doc is None or doc.deleted_at is not None:
        return None
    return await store.presign_get(doc.bucket, doc.object_key, doc.filename)


async def to_job_out(session: AsyncSession, job: Job, store: Storage | None = None) -> JobOut:
    return job_out(job, await download_url_for(session, job, store or get_storage()))


async def create_export_job(
    session: AsyncSession, user: User, key: str, fmt: str, params: ExportParams
) -> Job:
    d = get_authorized_definition(user, key)
    raw = params.as_dict()
    parse_params(raw)  # validates dates / uuids
    if user.role == "ADMIN" and key in STUDENT_KEYS and "student_id" not in raw:
        raise unprocessable("student_id is required", details=[{"field": "student_id", "message": "Required"}])
    job = Job(
        id=uuid.uuid4(),
        type="REPORT_EXPORT",
        status="QUEUED",
        requested_by=user.id,
        params={"report_key": d.meta.key, "format": fmt, "params": raw},
        progress=0,
    )
    session.add(job)
    side_effects.audit(session, user, "report.export", "job", job.id, after={"report": key, "format": fmt, "params": raw})
    side_effects.queue_task(session, "reports.export", {"job_id": str(job.id)})
    await session.flush()
    return job


async def get_job_for(session: AsyncSession, user: User, job_id: uuid.UUID) -> Job:
    job = (await session.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if job is None or (user.role != "ADMIN" and job.requested_by != user.id):
        raise not_found("Job not found")
    return job


async def list_jobs(
    session: AsyncSession, user: User, job_type: str | None, params: PageParams, store: Storage
) -> dict[str, Any]:
    stmt = select(Job).order_by(Job.created_at.desc())
    if user.role != "ADMIN":
        stmt = stmt.where(Job.requested_by == user.id)
    if job_type:
        stmt = stmt.where(Job.type == job_type)
    rows, total = await paginate(session, stmt, params)
    items = [await to_job_out(session, j, store) for j in rows]
    return make_page(items, total, params)


# --------------------------------------------------------------------------- worker entry point
async def _publish_job(user_id: uuid.UUID, out: JobOut) -> None:
    try:
        await side_effects.dispatcher.publish(user_id, {"type": "job", "data": out.model_dump(mode="json")})
    except Exception:  # noqa: BLE001 - live updates are best effort
        log.warning("could not publish job event for %s", out.id, exc_info=True)


async def _set_progress(session: AsyncSession, job: Job, progress: int, user_id: uuid.UUID | None) -> None:
    job.progress = progress
    await session.commit()
    if user_id is not None:
        await _publish_job(user_id, job_out(job))


def _filename(key: str, fmt: str, now: datetime) -> str:
    return f"{key}-{now.strftime('%Y%m%d-%H%M%S')}.{fmt}"


async def _execute(session: AsyncSession, job_id: uuid.UUID, store: Storage) -> None:
    job = (await session.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if job is None:
        log.warning("reports.export: job %s not found", job_id)
        return
    if job.type != "REPORT_EXPORT" or job.status == "SUCCEEDED":
        return
    user = None
    if job.requested_by is not None:
        user = (await session.execute(select(User).where(User.id == job.requested_by))).scalar_one_or_none()
    uid = user.id if user else None
    try:
        if user is None:
            raise RuntimeError("Requesting user no longer exists")
        key = str(job.params.get("report_key"))
        fmt = str(job.params.get("format"))
        if fmt not in CONTENT_TYPES:
            raise ValueError(f"Unsupported format {fmt!r}")
        d = get_authorized_definition(user, key)

        job.status, job.started_at, job.error = "RUNNING", utcnow(), None
        await _set_progress(session, job, 5, uid)

        data = await d.builder(session, user, dict(job.params.get("params") or {}))
        await _set_progress(session, job, 50, uid)

        if fmt == "pdf":
            payload = await anyio.to_thread.run_sync(render_pdf, data, user.full_name)
        else:
            payload = await anyio.to_thread.run_sync(render_xlsx, data)
        await _set_progress(session, job, 80, uid)

        now = utcnow()
        doc_id = uuid.uuid4()
        filename = _filename(key, fmt, now)
        object_key = f"{user.id}/{doc_id}/{filename}"
        bucket = settings.BUCKET_REPORTS
        await store.put_object(bucket, object_key, payload, CONTENT_TYPES[fmt])
        doc = Document(
            id=doc_id,
            owner_id=user.id,
            kind="REPORT",
            bucket=bucket,
            object_key=object_key,
            filename=filename,
            content_type=CONTENT_TYPES[fmt],
            size_bytes=len(payload),
            status="UPLOADED",
            verification_status="VERIFIED",
        )
        session.add(doc)
        await session.flush()
        job.result_document_id = doc.id
        job.result = {
            "rows_ok": sum(len(t.rows) for t in data.tables),
            "document_id": str(doc.id),
            "filename": filename,
            "format": fmt,
            "size_bytes": len(payload),
        }
        job.status, job.progress, job.finished_at = "SUCCEEDED", 100, utcnow()
        side_effects.notify(
            session,
            user.id,
            "REPORT_READY",
            f"{data.title} is ready",
            f"Your {fmt.upper()} export of {data.title} can be downloaded now.",
            link=report_link(user, key),
            data={"job_id": str(job.id), "document_id": str(doc.id), "report_key": key},
        )
        url = await store.presign_get(bucket, object_key, filename)
        await session.commit()
        await side_effects.flush(session)
        await _publish_job(user.id, job_out(job, url))
    except Exception as exc:  # noqa: BLE001 - record the failure on the job, never crash the worker
        log.exception("reports.export failed for job %s", job_id)
        await session.rollback()
        side_effects.discard(session)
        job = (await session.execute(select(Job).where(Job.id == job_id))).scalar_one()
        job.status, job.error, job.finished_at = "FAILED", str(exc)[:1000] or exc.__class__.__name__, utcnow()
        if user is not None:
            side_effects.notify(
                session, user.id, "REPORT_FAILED", "Report export failed", "Your report could not be generated.",
                link=report_link(user, str(job.params.get("report_key", ""))), data={"job_id": str(job.id)},
            )
        await session.commit()
        await side_effects.flush(session)
        if user is not None:
            await _publish_job(user.id, job_out(job))


async def run_export_job(
    job_id: uuid.UUID | str,
    *,
    session: AsyncSession | None = None,
    store: Storage | None = None,
) -> None:
    """Load the job, build + render the report, upload it, create the REPORT document, finish the job.

    Without ``session`` it creates its own NullPool engine (the worker path). Tests may inject a session / storage.
    """
    jid = job_id if isinstance(job_id, uuid.UUID) else uuid.UUID(str(job_id))
    store = store or get_storage()
    if session is not None:
        await _execute(session, jid, store)
        return
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as s:
            await _execute(s, jid, store)
    finally:
        await engine.dispose()

