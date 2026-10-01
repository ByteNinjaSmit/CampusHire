"""Application business rules (plan 3.7, 3.8, 4.4)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage as storage_mod
from app.core.base import utcnow
from app.core.errors import AppError, conflict, map_integrity_error, not_found, unprocessable
from app.core.pagination import PageParams, make_page
from app.core.permissions import can_manage_internship, can_view_application
from app.core.side_effects import audit, notify, queue_email
from app.core.types import MAX_RESUME_BYTES
from app.modules.applications import repository as repo
from app.modules.applications import schemas as s
from app.modules.applications.models import Application, ApplicationStatusHistory
from app.modules.applications.state_machine import (
    STATUS_LABELS,
    WITHDRAWN,
    allowed_targets,
    notify_owners,
    transition_application,
)
from app.modules.companies.models import Company
from app.modules.internships.models import Internship
from app.modules.users.models import User
from app.modules.users.schemas import DocumentSummary

# ---- builders ---------------------------------------------------------------------------------------


async def _logo(logo: tuple[str, str, str] | None) -> str | None:
    if not logo:
        return None
    try:
        return await storage_mod.get_storage().presign_get(logo[0], logo[1], logo[2])
    except Exception:  # noqa: BLE001
        return None


async def to_summaries(session: AsyncSession, user: User, apps: list[Application]) -> list[s.ApplicationSummary]:
    ctx = await repo.summary_context(session, apps, student_view=user.role == "STUDENT")
    logos: dict[uuid.UUID, str | None] = {}
    out: list[s.ApplicationSummary] = []
    for a in apps:
        i, company_name, logo = ctx["internships"][a.internship_id]
        if i.company_id not in logos:
            logos[i.company_id] = await _logo(logo)
        st = ctx["students"][a.student_id]
        out.append(
            s.ApplicationSummary(
                id=a.id,
                status=a.status,  # type: ignore[arg-type]  # validated into the enum
                status_changed_at=a.status_changed_at,
                created_at=a.created_at,
                internship=s.ApplicationInternshipRef(
                    id=i.id,
                    title=i.title,
                    company_id=i.company_id,
                    company_name=company_name,
                    company_logo_url=logos[i.company_id],
                    application_deadline=i.application_deadline,
                    start_date=i.start_date,
                ),
                student=s.ApplicationStudentRef(id=st[0], full_name=st[1], email=st[2], department=st[3], gpa=st[4]),
                next_interview_at=ctx["next_interview"].get(a.id),
                evaluation_avg=ctx["eval_avg"].get(a.id),
            )
        )
    return out


_STATUS_TITLES = {
    "PENDING": "Application submitted",
    "UNDER_REVIEW": "Moved to under review",
    "SHORTLISTED": "Shortlisted",
    "INTERVIEW": "Interview stage",
    "ACCEPTED": "Offer accepted by company",
    "REJECTED": "Application rejected",
    "WITHDRAWN": "Application withdrawn",
}


def _interview_dict(i: Any, student_name: str, internship: Internship, company_name: str, student_id: uuid.UUID, *, hide_comments: bool) -> dict[str, Any]:
    d = s.InterviewOut(
        id=i.id,
        application_id=i.application_id,
        scheduled_at=i.scheduled_at,
        duration_minutes=i.duration_minutes,
        mode=i.mode,
        location=i.location,
        meeting_link=i.meeting_link,
        interviewer_name=i.interviewer_name,
        interviewer_email=i.interviewer_email,
        status=i.status,
        result=i.result,
        score=i.score,
        comments=None if hide_comments else i.comments,
        feedback_for_student=i.feedback_for_student if (not hide_comments or i.status == "COMPLETED") else None,
        cancel_reason=i.cancel_reason,
        reschedule_count=i.reschedule_count,
        student=s.PersonRef(id=student_id, full_name=student_name),
        internship=s.InterviewInternshipRef(id=internship.id, title=internship.title, company_name=company_name),
        created_at=i.created_at,
    )
    return d


async def build_detail(session: AsyncSession, user: User, a: Application) -> s.ApplicationDetail:
    is_student = user.role == "STUDENT"
    summary = (await to_summaries(session, user, [a]))[0]
    internship = (await session.execute(select(Internship).where(Internship.id == a.internship_id))).scalar_one()
    resume = await repo.get_document(session, a.resume_document_id)
    assert resume is not None

    timeline: list[s.TimelineEvent] = []
    for h, actor_name in await repo.history_rows(session, a.id):
        note = h.note
        timeline.append(
            s.TimelineEvent(
                at=h.created_at,
                kind="STATUS",
                status=h.to_status,  # type: ignore[arg-type]
                title=_STATUS_TITLES.get(h.to_status, h.to_status),
                note=note,
                actor_name=actor_name,
            )
        )
    interviews: list[s.InterviewOut] = []
    for iv, scheduler in await repo.interview_rows(session, a.id):
        interviews.append(
            _interview_dict(
                iv, summary.student.full_name, internship, summary.internship.company_name, a.student_id, hide_comments=is_student
            )
        )
        timeline.append(s.TimelineEvent(at=iv.created_at, kind="INTERVIEW_SCHEDULED", title="Interview scheduled", note=iv.mode, actor_name=scheduler))
        if iv.reschedule_count > 0:
            timeline.append(s.TimelineEvent(at=iv.updated_at, kind="INTERVIEW_RESCHEDULED", title="Interview rescheduled", note=None, actor_name=scheduler))
        if iv.status == "CANCELLED":
            timeline.append(s.TimelineEvent(at=iv.updated_at, kind="INTERVIEW_CANCELLED", title="Interview cancelled", note=iv.cancel_reason, actor_name=scheduler))
        if iv.status in ("COMPLETED", "NO_SHOW"):
            timeline.append(
                s.TimelineEvent(
                    at=iv.updated_at,
                    kind="INTERVIEW_COMPLETED",
                    title="Interview completed" if iv.status == "COMPLETED" else "Interview: no show",
                    note=iv.result if iv.result != "PENDING" else None,
                    actor_name=None,
                )
            )
    evaluations: list[s.EvaluationSummaryOut] = []
    for ev, form_name, evaluator in await repo.evaluation_rows(session, a.id, shared_only=is_student):
        evaluations.append(
            s.EvaluationSummaryOut(
                id=ev.id,
                form_name=form_name,
                evaluator_name=evaluator,
                weighted_score=float(ev.weighted_score),
                recommendation=ev.recommendation,
                created_at=ev.created_at,
                shared_with_student=ev.shared_with_student,
            )
        )
        timeline.append(s.TimelineEvent(at=ev.created_at, kind="EVALUATION", title="Evaluation recorded", note=None, actor_name=evaluator if not is_student else None))
    if a.completed_at:
        timeline.append(s.TimelineEvent(at=a.completed_at, kind="COMPLETED", title="Internship completed"))
    timeline.sort(key=lambda e: e.at)

    sf_id, cf_ids = await repo.feedback_ids(session, a.id)
    today = datetime.now(UTC).date()
    can_feedback = (
        is_student
        and a.student_id == user.id
        and a.status == "ACCEPTED"
        and (a.completed_at is not None or internship.end_date <= today)
        and sf_id is None
    )
    role = "STUDENT" if is_student else user.role
    allowed = sorted(allowed_targets(role, a.status))
    return s.ApplicationDetail(
        **summary.model_dump(),
        cover_letter=a.cover_letter,
        qualifications=a.qualifications,
        answers=a.answers or {},
        resume=DocumentSummary.model_validate(resume),
        decision_note=a.decision_note,
        offer_details=a.offer_details,
        withdrawn_reason=a.withdrawn_reason,
        completed_at=a.completed_at,
        timeline=timeline,
        interviews=interviews,
        evaluations=evaluations,
        allowed_transitions=allowed,  # type: ignore[arg-type]
        can_give_student_feedback=can_feedback,
        student_feedback_id=sf_id,
        company_feedback_ids=cf_ids,
    )


# ---- queries --------------------------------------------------------------------------------------------
async def list_applications(
    session: AsyncSession,
    user: User,
    params: PageParams,
    *,
    statuses: list[str] | None = None,
    internship_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
    q: str | None = None,
) -> dict[str, Any]:
    bad = [x for x in (statuses or []) if x not in STATUS_LABELS]
    if bad:
        raise unprocessable("Invalid status filter", details=[{"field": "status", "message": f"Unknown status {bad[0]}"}])
    rows, total = await repo.list_page(
        session, user, params, statuses=statuses or [], internship_id=internship_id, student_id=student_id, q=q
    )
    return make_page(await to_summaries(session, user, rows), total, params)


async def get_visible(session: AsyncSession, user: User, application_id: uuid.UUID) -> Application:
    a = await repo.get(session, application_id)
    if a is None or not await can_view_application(session, user, a):
        raise not_found("Application not found")
    return a


async def get_detail(session: AsyncSession, user: User, application_id: uuid.UUID) -> s.ApplicationDetail:
    return await build_detail(session, user, await get_visible(session, user, application_id))


# ---- commands --------------------------------------------------------------------------------------------
async def _check_resume(session: AsyncSession, student_id: uuid.UUID, document_id: uuid.UUID | None):
    if document_id is None:
        raise unprocessable(
            "A resume (PDF, max 5 MB) is required",
            code="RESUME_REQUIRED",
            details=[{"field": "resume_document_id", "message": "Resume is required"}],
        )
    doc = await repo.get_document(session, document_id)
    ok = (
        doc is not None
        and doc.owner_id == student_id
        and doc.kind == "RESUME"
        and doc.status == "UPLOADED"
        and doc.deleted_at is None
        and doc.content_type == "application/pdf"
        and doc.size_bytes <= MAX_RESUME_BYTES
    )
    if not ok:
        raise unprocessable(
            "Resume must be one of your uploaded PDF resumes (max 5 MB)",
            code="RESUME_INVALID",
            details=[{"field": "resume_document_id", "message": "Invalid resume document"}],
        )
    return doc


async def submit(session: AsyncSession, user: User, data: s.ApplicationCreateRequest) -> Application:
    if user.email_verified_at is None:
        raise AppError(403, "EMAIL_NOT_VERIFIED", "Please verify your email address first")
    internship = (
        await session.execute(select(Internship).where(Internship.id == data.internship_id))
    ).scalar_one_or_none()
    if internship is None:
        raise not_found("Internship not found")
    if internship.status != "APPROVED" or internship.archived_at is not None:
        raise conflict("This internship is not open for applications", code="INTERNSHIP_NOT_OPEN")
    if internship.application_deadline <= utcnow():
        raise conflict("The application deadline has passed", code="DEADLINE_PASSED")
    await _check_resume(session, user.id, data.resume_document_id)
    student = await repo.get_student(session, user.id)
    if student is None:
        raise not_found("Student profile not found")
    problems: list[dict[str, str]] = []
    if internship.min_gpa is not None and student.gpa < internship.min_gpa:
        problems.append({"field": "gpa", "message": f"A minimum GPA of {internship.min_gpa} is required"})
    depts = {d.strip().lower() for d in (internship.eligible_departments or []) if d.strip()}
    if depts and student.department.strip().lower() not in depts:
        problems.append({"field": "department", "message": "Your department is not eligible for this internship"})
    if problems:
        raise unprocessable("You are not eligible for this internship", code="INELIGIBLE", details=problems)

    dup = (
        await session.execute(
            select(Application.id).where(
                Application.student_id == user.id, Application.internship_id == internship.id
            )
        )
    ).first()
    if dup:
        raise conflict("You have already applied to this internship", code="DUPLICATE_APPLICATION")

    now = utcnow()
    a = Application(
        id=uuid.uuid4(),
        internship_id=internship.id,
        student_id=user.id,
        resume_document_id=data.resume_document_id,
        cover_letter=data.cover_letter,
        qualifications=data.qualifications,
        answers=data.answers.model_dump(mode="json", exclude_none=True) if data.answers else {},
        status="PENDING",
        status_changed_at=now,
    )
    session.add(a)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise map_integrity_error(exc) from exc
    session.add(
        ApplicationStatusHistory(
            application_id=a.id, from_status=None, to_status="PENDING", changed_by=user.id, note=None, created_at=now
        )
    )
    await session.flush()

    company = (await session.execute(select(Company).where(Company.id == internship.company_id))).scalar_one()
    link = f"/student/applications/{a.id}"
    notify(
        session,
        user.id,
        "APPLICATION_STATUS",
        "Application submitted",
        f"Your application to {internship.title} at {company.name} was received",
        link,
        {"application_id": str(a.id), "internship_id": str(internship.id), "status": "PENDING"},
    )
    queue_email(
        session,
        "application_submitted",
        user.email,
        {
            "student_name": user.full_name,
            "internship_title": internship.title,
            "company_name": company.name,
            "application_id": str(a.id),
            "link": link,
        },
    )
    await notify_owners(
        session,
        internship,
        type="APPLICATION_RECEIVED",
        title="New application received",
        body=f"{user.full_name} applied to {internship.title}",
        data={"application_id": str(a.id), "internship_id": str(internship.id)},
    )
    audit(session, user, "application.create", "application", a.id, after={"internship_id": str(internship.id)})
    return a


async def update_status(
    session: AsyncSession, user: User, application_id: uuid.UUID, data: s.ApplicationStatusUpdateRequest
) -> Application:
    return await transition_application(
        session,
        application_id,
        data.status.value,
        user,
        note=data.note,
        offer_details=data.offer_details.model_dump(mode="json", exclude_none=True) if data.offer_details else None,
    )


async def bulk_status(session: AsyncSession, user: User, data: s.BulkStatusRequest) -> dict[str, Any]:
    updated: list[uuid.UUID] = []
    failed: list[dict[str, Any]] = []
    for aid in dict.fromkeys(data.ids):
        try:
            async with session.begin_nested():
                await transition_application(session, aid, data.status.value, user, note=data.note)
            updated.append(aid)
        except AppError as exc:
            failed.append({"id": aid, "code": exc.code, "message": exc.message})
    return {"updated": updated, "failed": failed}


async def withdraw(session: AsyncSession, user: User, application_id: uuid.UUID, reason: str | None) -> Application:
    return await transition_application(session, application_id, WITHDRAWN, user, note=reason)


async def complete(session: AsyncSession, user: User, application_id: uuid.UUID) -> Application:
    a = (
        await session.execute(
            select(Application)
            .where(Application.id == application_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if a is None:
        raise not_found("Application not found")
    internship = (await session.execute(select(Internship).where(Internship.id == a.internship_id))).scalar_one()
    if not await can_manage_internship(session, user, internship):
        raise not_found("Application not found")
    if a.status != "ACCEPTED":
        raise conflict("Only accepted applications can be completed", code="INVALID_STATUS_TRANSITION")
    if a.completed_at is not None:
        raise conflict("This internship is already marked as completed", code="CONFLICT")
    if user.role != "ADMIN" and datetime.now(UTC).date() < internship.end_date:
        raise conflict("The internship has not ended yet", code="CONFLICT")
    a.completed_at = utcnow()
    await session.flush()
    notify(
        session,
        a.student_id,
        "APPLICATION_COMPLETED",
        "Internship completed",
        f"{internship.title} is marked as completed. You can now share your feedback.",
        f"/student/applications/{a.id}",
        {"application_id": str(a.id), "internship_id": str(internship.id)},
    )
    audit(session, user, "application.complete", "application", a.id, after={"completed_at": a.completed_at.isoformat()})
    return a


async def resume_url(session: AsyncSession, user: User, application_id: uuid.UUID) -> dict[str, Any]:
    a = await get_visible(session, user, application_id)
    doc = await repo.get_document(session, a.resume_document_id)
    if doc is None:
        raise not_found("Resume not found")
    url = await storage_mod.get_storage().presign_get(
        doc.bucket, doc.object_key, doc.filename, expires=storage_mod.DOWNLOAD_TTL_SECONDS
    )
    return {"url": url, "expires_in": storage_mod.DOWNLOAD_TTL_SECONDS}
