"""Periodic maintenance (beat) and the on-demand compliance scan.

Each Celery task is a sync wrapper around an ``async def`` that takes an ``AsyncSession`` (so tests can call the
logic with their own session). The wrappers open a private NullPool session via ``runtime.worker_session``.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, delete, exists, func, not_, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import side_effects
from app.core.base import utcnow
from app.core.celery_app import celery_app
from app.modules.admin.models import CompliancePolicy, Job, PolicyViolation
from app.modules.applications.models import Application
from app.modules.auth.models import RefreshToken, UserToken
from app.modules.companies.models import Company
from app.modules.documents.models import Document
from app.modules.internships.models import Internship
from app.modules.interviews.models import Interview
from app.modules.students.models import Student
from app.modules.users.models import User
from app.workers.runtime import iso_z, publish_user_event, run_async, worker_session

log = logging.getLogger(__name__)

PENDING_UPLOAD_MAX_AGE = timedelta(hours=1)
TOKEN_GRACE = timedelta(days=1)
RESUME_UNVERIFIED_AFTER = timedelta(days=7)
# The 24 h notice rule is checked against ``now()`` in the service, while ``created_at`` is stamped a little
# later; the scan therefore only flags notice shorter than 24 h minus this tolerance.
SHORT_NOTICE_TOLERANCE = timedelta(minutes=5)
ACTIVE_APPLICATION_STATUSES = ("PENDING", "UNDER_REVIEW", "SHORTLISTED", "INTERVIEW")
LIVE_INTERNSHIP_STATUSES = ("PENDING_APPROVAL", "APPROVED")


# ---- close_expired_internships --------------------------------------------------------------------
async def close_expired_internships(session: AsyncSession) -> int:
    """APPROVED internships whose application deadline passed become CLOSED; the poster is notified."""
    now = utcnow()
    rows = (
        await session.execute(
            select(Internship.id, Internship.title, Internship.posted_by)
            .where(
                Internship.status == "APPROVED",
                Internship.application_deadline < now,
                Internship.archived_at.is_(None),
            )
            .with_for_update(skip_locked=True)
        )
    ).all()
    if not rows:
        return 0
    ids = [r.id for r in rows]
    await session.execute(update(Internship).where(Internship.id.in_(ids)).values(status="CLOSED", updated_at=now))
    for r in rows:
        side_effects.audit(
            session,
            None,
            "internship.auto_close",
            "internship",
            r.id,
            before={"status": "APPROVED"},
            after={"status": "CLOSED", "reason": "application deadline passed"},
        )
        side_effects.notify(
            session,
            r.posted_by,
            "INTERNSHIP_CLOSED",
            "Internship closed",
            f'"{r.title}" was closed automatically because its application deadline passed.',
            link=f"/internships/{r.id}",
            data={"internship_id": str(r.id)},
        )
    return len(ids)


@celery_app.task(name="maintenance.close_expired_internships")
def close_expired_internships_task() -> int:
    async def _run() -> int:
        async with worker_session() as session:
            return await close_expired_internships(session)

    closed = run_async(_run())
    log.info("closed %d expired internship(s)", closed)
    return closed


# ---- cleanup_tokens ---------------------------------------------------------------------------------
async def cleanup_tokens(session: AsyncSession) -> dict[str, int]:
    """Delete e-mail tokens that expired or were used, and refresh tokens that expired (1 day grace).

    Revoked-but-unexpired refresh tokens are kept: reuse detection needs them until they expire."""
    cutoff = utcnow() - TOKEN_GRACE
    user_tokens = await session.execute(
        delete(UserToken).where(or_(UserToken.expires_at < cutoff, UserToken.used_at < cutoff))
    )
    refresh = await session.execute(delete(RefreshToken).where(RefreshToken.expires_at < cutoff))
    return {
        "user_tokens": int(user_tokens.rowcount or 0),  # type: ignore[attr-defined]
        "refresh_tokens": int(refresh.rowcount or 0),  # type: ignore[attr-defined]
    }


@celery_app.task(name="maintenance.cleanup_tokens")
def cleanup_tokens_task() -> dict[str, int]:
    async def _run() -> dict[str, int]:
        async with worker_session() as session:
            return await cleanup_tokens(session)

    result = run_async(_run())
    log.info("token cleanup: %s", result)
    return result


# ---- purge_pending_uploads --------------------------------------------------------------------------
async def purge_pending_uploads(session: AsyncSession, delete_object: Any = None) -> int:
    """Remove documents stuck in PENDING_UPLOAD for over 1 h (row + any stray object).

    ``delete_object(bucket, key)`` is an async callable; defaults to the real storage."""
    if delete_object is None:
        from app.core.storage import storage

        delete_object = storage.delete
    cutoff = utcnow() - PENDING_UPLOAD_MAX_AGE
    stale = (
        await session.execute(
            select(Document.id, Document.bucket, Document.object_key)
            .where(
                Document.status == "PENDING_UPLOAD",
                Document.created_at < cutoff,
                not_(exists().where(Application.resume_document_id == Document.id)),
                not_(exists().where(Student.default_resume_id == Document.id)),
                not_(exists().where(Job.result_document_id == Document.id)),
            )
            .with_for_update(skip_locked=True)
        )
    ).all()
    for doc in stale:
        try:
            await delete_object(doc.bucket, doc.object_key)
        except Exception:  # noqa: BLE001 - missing object / storage hiccup must not block the row cleanup
            log.warning("could not delete object %s/%s", doc.bucket, doc.object_key, exc_info=True)
    if stale:
        await session.execute(delete(Document).where(Document.id.in_([d.id for d in stale])))
    return len(stale)


@celery_app.task(name="maintenance.purge_pending_uploads")
def purge_pending_uploads_task() -> int:
    async def _run() -> int:
        async with worker_session() as session:
            return await purge_pending_uploads(session)

    purged = run_async(_run())
    log.info("purged %d pending upload(s)", purged)
    return purged


# ---- compliance scan --------------------------------------------------------------------------------
# Each detector returns {entity_id: details} for entities that violate the policy right now.
async def _resume_unverified(session: AsyncSession, now: datetime) -> dict[uuid.UUID, dict[str, Any]]:
    rows = (
        await session.execute(
            select(Document.id, Document.owner_id, Document.created_at, func.array_agg(Application.id))
            .join(Application, Application.resume_document_id == Document.id)
            .where(
                Document.kind == "RESUME",
                Document.status == "UPLOADED",
                Document.verification_status == "PENDING",
                Document.deleted_at.is_(None),
                Document.created_at < now - RESUME_UNVERIFIED_AFTER,
                Application.status.in_(ACTIVE_APPLICATION_STATUSES),
            )
            .group_by(Document.id)
        )
    ).all()
    return {
        r[0]: {"owner_id": str(r[1]), "uploaded_at": iso_z(r[2]), "application_ids": [str(a) for a in r[3]]}
        for r in rows
    }


async def _past_deadline_open(session: AsyncSession, now: datetime) -> dict[uuid.UUID, dict[str, Any]]:
    rows = (
        await session.execute(
            select(Internship.id, Internship.title, Internship.application_deadline).where(
                Internship.status == "APPROVED",
                Internship.application_deadline < now,
                Internship.archived_at.is_(None),
            )
        )
    ).all()
    return {r.id: {"title": r.title, "application_deadline": iso_z(r.application_deadline)} for r in rows}


async def _interview_short_notice(session: AsyncSession, now: datetime) -> dict[uuid.UUID, dict[str, Any]]:
    rows = (
        await session.execute(
            select(Interview.id, Interview.application_id, Interview.scheduled_at, Interview.created_at).where(
                Interview.reschedule_count == 0,
                Interview.scheduled_at >= Interview.created_at,
                Interview.scheduled_at < Interview.created_at + (timedelta(hours=24) - SHORT_NOTICE_TOLERANCE),
            )
        )
    ).all()
    return {
        r.id: {
            "application_id": str(r.application_id),
            "scheduled_at": iso_z(r.scheduled_at),
            "created_at": iso_z(r.created_at),
            "notice_hours": round((r.scheduled_at - r.created_at).total_seconds() / 3600, 2),
        }
        for r in rows
    }


async def _unpaid_long(session: AsyncSession, now: datetime) -> dict[uuid.UUID, dict[str, Any]]:
    rows = (
        await session.execute(
            select(Internship.id, Internship.title, Internship.duration_weeks).where(
                Internship.stipend_monthly == 0,
                Internship.duration_weeks > 12,
                Internship.status.in_(LIVE_INTERNSHIP_STATUSES),
                Internship.archived_at.is_(None),
            )
        )
    ).all()
    return {r.id: {"title": r.title, "duration_weeks": r.duration_weeks, "stipend_monthly": 0} for r in rows}


async def _inactive_company(session: AsyncSession, now: datetime) -> dict[uuid.UUID, dict[str, Any]]:
    rows = (
        await session.execute(
            select(Internship.id, Internship.title, Company.id, Company.name, Company.status)
            .join(Company, Company.id == Internship.company_id)
            .where(
                or_(Company.status.in_(("ARCHIVED", "PENDING")), Company.archived_at.is_not(None)),
                Internship.status.in_(LIVE_INTERNSHIP_STATUSES),
                Internship.archived_at.is_(None),
            )
        )
    ).all()
    return {r[0]: {"title": r[1], "company_id": str(r[2]), "company_name": r[3], "company_status": r[4]} for r in rows}


DETECTORS: dict[str, tuple[str, Any]] = {
    "RESUME_UNVERIFIED_7D": ("document", _resume_unverified),
    "INTERNSHIP_PAST_DEADLINE_OPEN": ("internship", _past_deadline_open),
    "INTERVIEW_SHORT_NOTICE": ("interview", _interview_short_notice),
    "UNPAID_LONG_INTERNSHIP": ("internship", _unpaid_long),
    "INACTIVE_COMPANY_POSTING": ("internship", _inactive_company),
}


async def run_compliance_scan(session: AsyncSession) -> dict[str, Any]:
    """Evaluate every active policy. Idempotent: ``(policy, entity_type, entity_id)`` is unique, so re-running
    only inserts violations that are new and auto-resolves OPEN ones whose condition no longer holds
    (DISMISSED / RESOLVED rows are left alone). Returns a JSON summary."""
    now = utcnow()
    policies = (
        (await session.execute(select(CompliancePolicy).where(CompliancePolicy.is_active.is_(True)))).scalars().all()
    )
    summary: dict[str, Any] = {"policies_checked": 0, "new_violations": 0, "auto_resolved": 0, "per_policy": {}}
    for policy in policies:
        detector = DETECTORS.get(policy.code)
        if detector is None:
            continue
        entity_type, fn = detector
        found: dict[uuid.UUID, dict[str, Any]] = await fn(session, now)
        new = 0
        for entity_id, details in found.items():
            res = await session.execute(
                pg_insert(PolicyViolation)
                .values(
                    policy_id=policy.id, entity_type=entity_type, entity_id=entity_id, details=details, status="OPEN"
                )
                .on_conflict_do_nothing(constraint="uq_policy_violations_policy_entity")
                .returning(PolicyViolation.id)
            )
            if res.first() is not None:
                new += 1
        stale_filter = and_(
            PolicyViolation.policy_id == policy.id,
            PolicyViolation.entity_type == entity_type,
            PolicyViolation.status == "OPEN",
        )
        if found:
            stale_filter = and_(stale_filter, PolicyViolation.entity_id.not_in(list(found)))
        resolved = await session.execute(
            update(PolicyViolation)
            .where(stale_filter)
            .values(status="RESOLVED", resolved_at=now, note="Auto-resolved: condition no longer holds")
        )
        n_resolved = int(resolved.rowcount or 0)  # type: ignore[attr-defined]
        summary["policies_checked"] += 1
        summary["new_violations"] += new
        summary["auto_resolved"] += n_resolved
        summary["per_policy"][policy.code] = {"current": len(found), "new": new, "auto_resolved": n_resolved}
    open_total = (
        await session.execute(select(func.count()).select_from(PolicyViolation).where(PolicyViolation.status == "OPEN"))
    ).scalar_one()
    summary["open_violations"] = int(open_total)
    return summary


async def _notify_admins(session: AsyncSession, summary: dict[str, Any]) -> None:
    if not summary["new_violations"]:
        return
    admins = (
        (await session.execute(select(User.id).where(User.role == "ADMIN", User.is_active.is_(True)))).scalars().all()
    )
    for admin_id in admins:
        side_effects.notify(
            session,
            admin_id,
            "COMPLIANCE_VIOLATIONS",
            "New compliance violations",
            f"The compliance scan found {summary['new_violations']} new violation(s); {summary['open_violations']} open in total.",
            link="/admin/compliance",
            data={"new": summary["new_violations"], "open": summary["open_violations"]},
        )


async def _job_payload(job: Job) -> dict[str, Any]:
    return {
        "id": str(job.id),
        "type": job.type,
        "status": job.status,
        "progress": job.progress,
        "params": job.params,
        "result": job.result,
        "error": job.error,
        "download_url": None,
        "created_at": iso_z(job.created_at),
        "finished_at": iso_z(job.finished_at),
    }


async def compliance_scan_job(job_id: uuid.UUID | None = None) -> dict[str, Any]:
    """Run the scan tracked by a ``jobs`` row (created here when beat calls without ``job_id``)."""
    async with worker_session() as session:
        job: Job | None = await session.get(Job, job_id) if job_id else None
        if job is None:
            job = Job(type="COMPLIANCE_SCAN", status="RUNNING", requested_by=None, params={"trigger": "schedule"})
            session.add(job)
        job.status, job.started_at, job.progress = "RUNNING", utcnow(), 10
        await session.flush()
        requester = job.requested_by
        if requester:
            await publish_user_event(requester, {"type": "job", "data": await _job_payload(job)})
        try:
            async with session.begin_nested():
                summary = await run_compliance_scan(session)
        except Exception as exc:
            job.status, job.error, job.finished_at = "FAILED", f"{type(exc).__name__}: {exc}"[:2000], utcnow()
            await session.flush()
            if requester:
                await publish_user_event(requester, {"type": "job", "data": await _job_payload(job)})
            await session.commit()
            raise
        job.status, job.progress, job.result, job.finished_at = "SUCCEEDED", 100, summary, utcnow()
        await _notify_admins(session, summary)
        await session.flush()
        if requester:
            await publish_user_event(requester, {"type": "job", "data": await _job_payload(job)})
        return summary


@celery_app.task(name="maintenance.compliance_scan")
def compliance_scan(job_id: str | None = None) -> dict[str, Any]:
    summary = run_async(compliance_scan_job(uuid.UUID(job_id) if job_id else None))
    log.info("compliance scan: %s", summary)
    return summary
