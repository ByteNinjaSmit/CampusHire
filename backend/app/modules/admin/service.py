"""Admin business logic: audit browser, metrics, compliance (policies / scan / violations), jobs, export / import."""

import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, exists, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import redis as redis_core
from app.core import side_effects
from app.core.base import utcnow
from app.core.config import settings
from app.core.errors import conflict, not_found, unprocessable
from app.core.middleware import LATENCY_BUCKETS_MS, metrics_key
from app.core.pagination import PageParams, make_page, paginate
from app.core.side_effects import audit, queue_task
from app.core.storage import DOWNLOAD_TTL_SECONDS, Storage
from app.modules.admin import exporter, importer
from app.modules.admin import repository as repo
from app.modules.admin import schemas as s
from app.modules.admin.exporter import _fail
from app.modules.admin.models import CompliancePolicy, Job, PolicyViolation
from app.modules.applications.models import Application
from app.modules.companies.models import Company
from app.modules.documents.models import Document
from app.modules.internships.models import Internship
from app.modules.interviews.models import Interview
from app.modules.users.models import User

log = logging.getLogger(__name__)

ADMIN_JOB_TYPES = ["DATA_EXPORT", "DATA_IMPORT", "COMPLIANCE_SCAN"]
_SLUG = re.compile(r"[^A-Za-z0-9._-]+")


# ===== audit logs ===============================================================================================
def _actor(uid: Any, name: str | None, role: str | None) -> s.ActorRef | None:
    if uid is None or name is None or role is None:
        return None
    return s.ActorRef(id=uid, full_name=name, role=role)  # type: ignore[arg-type]  # role validated by pydantic


async def list_audit_logs(
    session: AsyncSession,
    params: PageParams,
    actor_id: uuid.UUID | None,
    entity_type: str | None,
    action: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> dict[str, Any]:
    rows, total = await paginate(
        session, repo.audit_query(actor_id, entity_type, action, date_from, date_to), params, scalars=False
    )
    items = [
        s.AuditLogOut(
            id=log_row.id,
            actor=_actor(user.id, user.full_name, user.role) if user else None,
            action=log_row.action,
            entity_type=log_row.entity_type,
            entity_id=log_row.entity_id,
            before=log_row.before,
            after=log_row.after,
            ip=str(log_row.ip) if log_row.ip else None,
            user_agent=log_row.user_agent,
            created_at=log_row.created_at,
        )
        for log_row, user in rows
    ]
    return make_page(items, total, params)


# ===== metrics ====================================================================================================
def _percentile(hist: list[tuple[float, int]], q: float) -> float | None:
    """Estimate a latency percentile (ms) from ``[(upper_bound_ms, count)]`` with linear interpolation."""
    total = sum(c for _, c in hist)
    if total == 0:
        return None
    target = q * total
    cum = 0
    lower = 0.0
    for upper, count in hist:
        if count and cum + count >= target:
            return round(lower + (upper - lower) * (target - cum) / count, 1)
        cum += count
        lower = upper
    return round(lower, 1)


def _hist_of(raw: dict[str, str]) -> list[tuple[float, int]]:
    bounds = list(LATENCY_BUCKETS_MS)
    hist = [(float(b), int(raw.get(f"lat_le_{b}", 0))) for b in bounds]
    # the open-ended bucket is reported at the last bound (we only know "slower than that")
    hist.append((float(bounds[-1]), int(raw.get("lat_le_inf", 0))))
    return hist


async def get_metrics(session: AsyncSession, minutes: int, login_days: int) -> s.MetricsResponse:
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    stamps = [now - timedelta(minutes=i) for i in range(minutes - 1, -1, -1)]
    r = redis_core.get_redis()
    pipe = r.pipeline(transaction=False)
    for ts in stamps:
        pipe.hgetall(metrics_key(ts))
    raws: list[dict[str, str]] = await pipe.execute()

    points: list[s.MetricPoint] = []
    agg = [0.0] * len(LATENCY_BUCKETS_MS)
    agg_inf = 0
    requests = errors = 0
    lat_sum = 0.0
    for ts, raw in zip(stamps, raws, strict=True):
        count = int(raw.get("count", 0))
        errs = int(raw.get("errors", 0))
        hist = _hist_of(raw)
        requests += count
        errors += errs
        lat_sum += float(raw.get("lat_sum_ms", 0))
        for i, (_, c) in enumerate(hist[:-1]):
            agg[i] += c
        agg_inf += hist[-1][1]
        points.append(
            s.MetricPoint(
                minute=ts, requests=count, errors=errs, p50_ms=_percentile(hist, 0.5), p95_ms=_percentile(hist, 0.95)
            )
        )
    total_hist = [(float(b), int(c)) for b, c in zip(LATENCY_BUCKETS_MS, agg, strict=True)]
    total_hist.append((float(LATENCY_BUCKETS_MS[-1]), agg_inf))
    totals = s.MetricTotals(
        requests=requests,
        errors=errors,
        error_rate=round(errors / requests, 4) if requests else 0.0,
        avg_ms=round(lat_sum / requests, 1) if requests else None,
        p50_ms=_percentile(total_hist, 0.5),
        p95_ms=_percentile(total_hist, 0.95),
    )

    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    since = today - timedelta(days=login_days - 1)
    by_day = {d.date(): (ok, bad) for d, ok, bad in await repo.login_trend(session, since)}
    trend = [
        s.LoginTrendPoint(
            date=(since + timedelta(days=i)).date(),
            success=by_day.get((since + timedelta(days=i)).date(), (0, 0))[0],
            failed=by_day.get((since + timedelta(days=i)).date(), (0, 0))[1],
        )
        for i in range(login_days)
    ]
    return s.MetricsResponse(
        minutes=minutes,
        points=points,
        totals=totals,
        login_trend=trend,
        active_users_24h=await repo.active_users_since(session, utcnow() - timedelta(hours=24)),
        logins_last_hour=await repo.logins_since(session, utcnow() - timedelta(hours=1)),
    )


# ===== compliance: policies / violations ============================================================================
def _policy_out(p: CompliancePolicy, open_violations: int) -> s.PolicyOut:
    return s.PolicyOut(
        id=p.id,
        code=p.code,
        name=p.name,
        description=p.description,
        is_active=p.is_active,
        severity=p.severity,
        open_violations=open_violations,
        created_at=p.created_at,
    )


async def list_policies(session: AsyncSession) -> list[s.PolicyOut]:
    return [_policy_out(p, n) for p, n in await repo.list_policies(session)]


async def create_policy(session: AsyncSession, admin: User, data: s.PolicyCreate) -> s.PolicyOut:
    if await repo.get_policy_by_code(session, data.code):
        raise conflict("A policy with this code already exists")
    policy = CompliancePolicy(
        id=uuid.uuid4(),
        code=data.code,
        name=data.name,
        description=data.description,
        severity=data.severity,
        is_active=data.is_active,
    )
    session.add(policy)
    await session.flush()
    audit(
        session,
        admin,
        "compliance.policy.create",
        "compliance_policy",
        policy.id,
        after={"code": policy.code, "is_active": policy.is_active},
    )
    return _policy_out(policy, 0)


async def update_policy(session: AsyncSession, admin: User, policy_id: uuid.UUID, data: s.PolicyUpdate) -> s.PolicyOut:
    policy = await repo.get_policy(session, policy_id)
    if policy is None:
        raise not_found("Policy not found")
    before = {
        "name": policy.name,
        "description": policy.description,
        "severity": policy.severity,
        "is_active": policy.is_active,
    }
    for field in data.model_fields_set:
        value = getattr(data, field)
        if value is None and field != "description":
            continue  # NOT NULL columns
        setattr(policy, field, value)
    await session.flush()
    after = {
        "name": policy.name,
        "description": policy.description,
        "severity": policy.severity,
        "is_active": policy.is_active,
    }
    audit(session, admin, "compliance.policy.update", "compliance_policy", policy.id, before=before, after=after)
    return _policy_out(policy, await repo.open_violation_count(session, policy.id))


def _violation_out(row: Any) -> s.ViolationOut:
    v, p, rid, rname, rrole = row
    return s.ViolationOut(
        id=v.id,
        policy=s.PolicyRef(id=p.id, code=p.code, name=p.name, severity=p.severity),
        entity_type=v.entity_type,
        entity_id=v.entity_id,
        details=v.details or {},
        status=v.status,  # type: ignore[arg-type]  # CHECK-constrained literal
        resolved_by=_actor(rid, rname, rrole),
        resolved_at=v.resolved_at,
        note=v.note,
        created_at=v.created_at,
    )


async def list_violations(
    session: AsyncSession, params: PageParams, status: str | None, policy_code: str | None
) -> dict[str, Any]:
    rows, total = await paginate(session, repo.violations_query(status, policy_code), params, scalars=False)
    return make_page([_violation_out(r) for r in rows], total, params)


async def update_violation(
    session: AsyncSession, admin: User, violation_id: uuid.UUID, data: s.ViolationUpdate
) -> s.ViolationOut:
    v = await repo.get_violation(session, violation_id)
    if v is None:
        raise not_found("Violation not found")
    before = {"status": v.status, "note": v.note}
    v.status = data.status
    if "note" in data.model_fields_set:
        v.note = data.note
    if data.status == "OPEN":
        v.resolved_by = None
        v.resolved_at = None
    else:
        v.resolved_by = admin.id
        v.resolved_at = utcnow()
    await session.flush()
    audit(
        session,
        admin,
        f"compliance.violation.{data.status.lower()}",
        "policy_violation",
        v.id,
        before=before,
        after={"status": v.status, "note": v.note},
    )
    rows, _ = await paginate(
        session, repo.violations_query(None, None).where(PolicyViolation.id == v.id), PageParams(1, 1), scalars=False
    )
    return _violation_out(rows[0])


async def list_document_queue(
    session: AsyncSession, params: PageParams, verification_status: str, kind: str | None
) -> dict[str, Any]:
    rows, total = await paginate(session, repo.document_queue_query(verification_status, kind), params, scalars=False)
    items = [
        s.DocumentQueueItem(
            id=d.id,
            kind=d.kind,
            filename=d.filename,
            content_type=d.content_type,
            size_bytes=d.size_bytes,
            status=d.status,
            verification_status=d.verification_status,
            owner=s.OwnerRef(id=u.id, full_name=u.full_name, email=u.email),
            active_applications=int(n),
            created_at=d.created_at,
        )
        for d, u, n in rows
    ]
    return make_page(items, total, params)


# ===== compliance scan ==============================================================================================
Detection = tuple[str, uuid.UUID, dict[str, Any]]


def _iso(dt: datetime | None) -> str | None:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z") if dt else None


async def _detect_resume_unverified(session: AsyncSession, now: datetime) -> list[Detection]:
    cutoff = now - timedelta(days=7)
    active_app = exists().where(
        Application.resume_document_id == Document.id, Application.status.notin_(("REJECTED", "WITHDRAWN"))
    )
    rows = await session.execute(
        select(Document.id, Document.filename, Document.owner_id, Document.created_at).where(
            Document.kind == "RESUME",
            Document.status == "UPLOADED",
            Document.deleted_at.is_(None),
            Document.verification_status == "PENDING",
            Document.created_at < cutoff,
            active_app,
        )
    )
    return [
        ("document", i, {"filename": fn, "owner_id": str(o), "uploaded_at": _iso(c), "days_pending": (now - c).days})
        for i, fn, o, c in rows.all()
    ]


async def _detect_past_deadline_open(session: AsyncSession, now: datetime) -> list[Detection]:
    rows = await session.execute(
        select(Internship.id, Internship.title, Internship.application_deadline).where(
            Internship.status == "APPROVED",
            Internship.archived_at.is_(None),
            Internship.application_deadline < now,
        )
    )
    return [("internship", i, {"title": t, "application_deadline": _iso(d)}) for i, t, d in rows.all()]


async def _detect_short_notice(session: AsyncSession, now: datetime) -> list[Detection]:
    rows = await session.execute(
        select(Interview.id, Interview.application_id, Interview.scheduled_at, Interview.created_at).where(
            Interview.status.in_(("SCHEDULED", "RESCHEDULED")),
            Interview.reschedule_count == 0,
            Interview.scheduled_at - Interview.created_at < timedelta(hours=24),
        )
    )
    return [
        (
            "interview",
            i,
            {
                "application_id": str(a),
                "scheduled_at": _iso(sa),
                "created_at": _iso(ca),
                "notice_hours": round((sa - ca).total_seconds() / 3600, 1),
            },
        )
        for i, a, sa, ca in rows.all()
    ]


async def _detect_unpaid_long(session: AsyncSession, now: datetime) -> list[Detection]:
    rows = await session.execute(
        select(Internship.id, Internship.title, Internship.duration_weeks).where(
            Internship.stipend_monthly == 0,
            Internship.duration_weeks > 12,
            Internship.archived_at.is_(None),
            Internship.status.in_(("PENDING_APPROVAL", "APPROVED")),
        )
    )
    return [("internship", i, {"title": t, "duration_weeks": w, "stipend_monthly": 0}) for i, t, w in rows.all()]


async def _detect_inactive_company(session: AsyncSession, now: datetime) -> list[Detection]:
    rows = await session.execute(
        select(Internship.id, Internship.title, Company.id, Company.name, Company.status)
        .join(Company, Company.id == Internship.company_id)
        .where(
            and_(
                Company.status.in_(("ARCHIVED", "PENDING")),
                Internship.archived_at.is_(None),
                Internship.status.in_(("PENDING_APPROVAL", "APPROVED")),
            )
        )
    )
    return [
        ("internship", i, {"title": t, "company_id": str(ci), "company": cn, "company_status": cs})
        for i, t, ci, cn, cs in rows.all()
    ]


DETECTORS = {
    "RESUME_UNVERIFIED_7D": _detect_resume_unverified,
    "INTERNSHIP_PAST_DEADLINE_OPEN": _detect_past_deadline_open,
    "INTERVIEW_SHORT_NOTICE": _detect_short_notice,
    "UNPAID_LONG_INTERNSHIP": _detect_unpaid_long,
    "INACTIVE_COMPANY_POSTING": _detect_inactive_company,
}


async def run_compliance_scan(session: AsyncSession) -> dict[str, Any]:
    """Evaluate every active policy and record violations. Idempotent (unique policy/entity pair).

    * New findings are inserted as OPEN; existing rows (any status) are left untouched.
    * OPEN violations whose condition no longer holds are auto-resolved.

    Flushes but does not commit; callable from the seed (plain async function) and from the Celery task.
    """
    now = utcnow()
    policies = (
        (await session.execute(select(CompliancePolicy).where(CompliancePolicy.is_active.is_(True)))).scalars().all()
    )
    by_policy: dict[str, int] = {}
    auto_resolved = 0
    checked = 0
    for policy in policies:
        detector = DETECTORS.get(policy.code)
        if detector is None:
            continue  # custom (manual) policy: no automatic detector
        checked += 1
        found = await detector(session, now)
        new = 0
        for start in range(0, len(found), 500):
            chunk = found[start : start + 500]
            res = await session.execute(
                pg_insert(PolicyViolation)
                .values(
                    [
                        {
                            "id": uuid.uuid4(),
                            "policy_id": policy.id,
                            "entity_type": et,
                            "entity_id": eid,
                            "details": details,
                            "status": "OPEN",
                            "created_at": now,
                            "updated_at": now,
                        }
                        for et, eid, details in chunk
                    ]
                )
                .on_conflict_do_nothing(constraint="uq_policy_violations_policy_entity")
                .returning(PolicyViolation.id)
            )
            new += len(res.all())
        by_policy[policy.code] = new
        ids = [eid for _, eid, _ in found]
        stale = update(PolicyViolation).where(PolicyViolation.policy_id == policy.id, PolicyViolation.status == "OPEN")
        if ids:
            stale = stale.where(PolicyViolation.entity_id.notin_(ids))
        res = await session.execute(
            stale.values(status="RESOLVED", resolved_at=now, note="Auto-resolved: condition no longer holds")
        )
        auto_resolved += res.rowcount or 0
    await session.flush()
    open_total = (
        await session.execute(select(func.count()).select_from(PolicyViolation).where(PolicyViolation.status == "OPEN"))
    ).scalar_one()
    return {
        "policies_checked": checked,
        "new_violations": sum(by_policy.values()),
        "auto_resolved": auto_resolved,
        "open_total": int(open_total),
        "by_policy": by_policy,
    }


async def create_scan_job(session: AsyncSession, admin: User) -> s.Job:
    job = Job(id=uuid.uuid4(), type="COMPLIANCE_SCAN", status="QUEUED", requested_by=admin.id, params={})
    session.add(job)
    await session.flush()
    audit(session, admin, "compliance.scan", "job", job.id)
    queue_task(session, "maintenance.compliance_scan", {"job_id": str(job.id)})
    return s.job_out(job)


async def run_compliance_scan_job(
    job_id: uuid.UUID | str | None = None, *, session_factory: repo.SessionFactory | None = None
) -> dict[str, Any] | None:
    """Celery entry point for ``maintenance.compliance_scan``. ``job_id=None`` (beat) creates its own job row."""
    async with repo.worker_session(session_factory) as session:
        job: Job | None
        if job_id is None:
            job = Job(id=uuid.uuid4(), type="COMPLIANCE_SCAN", status="QUEUED", requested_by=None, params={})
            session.add(job)
            await session.commit()
        else:
            job = await repo.get_job(session, uuid.UUID(str(job_id)))
            if job is None:
                log.error("compliance job %s not found", job_id)
                return None
        jid = job.id
        try:
            job.status = "RUNNING"
            job.started_at = utcnow()
            job.progress = 10
            await session.commit()
            result = await run_compliance_scan(session)
            job = await repo.get_job(session, jid)
            assert job is not None
            job.result = {"rows_ok": result["new_violations"], "rows_failed": 0, **result}
            job.status = "SUCCEEDED"
            job.progress = 100
            job.finished_at = utcnow()
            audit(session, job.requested_by, "compliance.scan.complete", "job", job.id, after=result)
            if job.requested_by is not None:
                side_effects.notify(
                    session,
                    job.requested_by,
                    "SYSTEM",
                    "Compliance scan finished",
                    f"{result['new_violations']} new violation(s), {result['open_total']} open in total.",
                    link="/admin/compliance",
                    data={"job_id": str(job.id)},
                )
            await session.commit()
            await side_effects.flush(session)
            await exporter._publish(job)
            return result
        except Exception as exc:  # noqa: BLE001
            log.exception("compliance scan job %s failed", jid)
            await _fail(session, jid, str(exc) or type(exc).__name__)
            return None


# ===== jobs ===========================================================================================================
async def job_download_url(session: AsyncSession, job: Job, store: Storage) -> str | None:
    if job.status != "SUCCEEDED" or job.result_document_id is None:
        return None
    doc = await repo.get_document(session, job.result_document_id)
    if doc is None or doc.deleted_at is not None:
        return None
    return await store.presign_get(doc.bucket, doc.object_key, doc.filename)


async def list_jobs(
    session: AsyncSession, params: PageParams, type_: str | None, status: str | None, store: Storage
) -> dict[str, Any]:
    rows, total = await paginate(session, repo.jobs_query(ADMIN_JOB_TYPES, type_, status), params)
    items = [s.job_out(j, await job_download_url(session, j, store)) for j in rows]
    return make_page(items, total, params)


async def get_job(session: AsyncSession, job_id: uuid.UUID, store: Storage) -> s.Job:
    job = await repo.get_job(session, job_id)
    if job is None or job.type not in ADMIN_JOB_TYPES:
        raise not_found("Job not found")
    return s.job_out(job, await job_download_url(session, job, store))


async def get_job_download(session: AsyncSession, job_id: uuid.UUID, store: Storage) -> s.JobDownload:
    job = await repo.get_job(session, job_id)
    if job is None or job.type not in ADMIN_JOB_TYPES:
        raise not_found("Job not found")
    url = await job_download_url(session, job, store)
    if url is None:
        raise not_found("This job has no downloadable file")
    return s.JobDownload(url=url, expires_in=DOWNLOAD_TTL_SECONDS)


# ===== export / import ================================================================================================
async def create_export_job(session: AsyncSession, admin: User, data: s.ExportRequest) -> s.Job:
    try:
        filters = exporter.parse_filters(data.entity, data.filters)
    except ValueError as exc:
        field, _, message = str(exc).partition(": ")
        raise unprocessable(
            "Invalid export filters", details=[{"field": f"filters.{field}", "message": message or str(exc)}]
        ) from exc
    params = {
        "entity": data.entity,
        "format": data.format,
        "filters": {k: (str(v) if not isinstance(v, (bool, int, float, str)) else v) for k, v in filters.items()},
    }
    job = Job(id=uuid.uuid4(), type="DATA_EXPORT", status="QUEUED", requested_by=admin.id, params=params)
    session.add(job)
    await session.flush()
    audit(session, admin, "data.export", "job", job.id, after=params)
    queue_task(session, "data.export", {"job_id": str(job.id)})
    return s.job_out(job)


async def create_import_job(
    session: AsyncSession,
    admin: User,
    entity: str,
    filename: str,
    data: bytes,
    store: Storage,
) -> s.Job:
    name = (filename or "").strip()
    lower = name.lower()
    if not lower.endswith(importer.ALLOWED_EXTENSIONS):
        raise unprocessable(
            "Only .csv and .xlsx files are supported", details=[{"field": "file", "message": "Unsupported file type"}]
        )
    if not data:
        raise unprocessable("The file is empty", details=[{"field": "file", "message": "Empty file"}])
    if len(data) > importer.MAX_IMPORT_BYTES:
        raise unprocessable(
            "File exceeds the 5 MB limit",
            code="FILE_TOO_LARGE",
            details=[{"field": "file", "message": "Maximum size is 5 MB"}],
        )
    if lower.endswith(".xlsx") and data[:2] != b"PK":
        raise unprocessable(
            "The file is not a valid .xlsx workbook", details=[{"field": "file", "message": "Invalid xlsx"}]
        )
    if lower.endswith(".csv") and b"\x00" in data[:4096]:
        raise unprocessable("The file is not a valid CSV", details=[{"field": "file", "message": "Binary content"}])
    try:  # fail fast on unusable files (bad format / missing columns); row errors are reported by the job
        headers, _rows = importer.parse_rows(name, data)
    except importer.ImportFileError as exc:
        raise unprocessable(str(exc), details=[{"field": "file", "message": str(exc)}]) from exc
    missing = [c for c in importer.REQUIRED[entity] if c not in headers]
    if missing:
        msg = f"Missing required column(s): {', '.join(missing)}"
        raise unprocessable(msg, details=[{"field": "file", "message": msg}])

    doc_id = uuid.uuid4()
    content_type = exporter.XLSX_TYPE if lower.endswith(".xlsx") else exporter.CSV_TYPE
    key = f"{admin.id}/{doc_id}/{_SLUG.sub('-', name)[:200]}"
    await store.put_object(settings.BUCKET_DOCUMENTS, key, data, content_type)
    session.add(
        Document(
            id=doc_id,
            owner_id=admin.id,
            kind="IMPORT",
            bucket=settings.BUCKET_DOCUMENTS,
            object_key=key,
            filename=name[:255],
            content_type=content_type,
            size_bytes=len(data),
            status="UPLOADED",
            verification_status="VERIFIED",
        )
    )
    await session.flush()
    params = {"entity": entity, "filename": name[:255], "document_id": str(doc_id)}
    job = Job(id=uuid.uuid4(), type="DATA_IMPORT", status="QUEUED", requested_by=admin.id, params=params)
    session.add(job)
    await session.flush()
    audit(session, admin, "data.import", "job", job.id, after=params)
    queue_task(session, "data.import", {"job_id": str(job.id)})
    return s.job_out(job)
