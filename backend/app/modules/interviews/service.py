"""Interview scheduling rules R1-R5 (plan 3.9) and role-scoped reads."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import utcnow
from app.core.config import settings
from app.core.errors import AppError, conflict, forbidden, not_found, unprocessable
from app.core.pagination import PageParams, make_page, paginate
from app.core.permissions import can_manage_internship
from app.core.side_effects import audit, notify, queue_email
from app.modules.applications.models import Application, ApplicationStatusHistory
from app.modules.companies.models import Company
from app.modules.internships.models import Internship
from app.modules.interviews import repository as repo
from app.modules.interviews import schemas as s
from app.modules.interviews.models import Interview
from app.modules.users.models import User

NOTICE = timedelta(hours=24)
SCHEDULABLE_APPLICATION_STATUSES = ("SHORTLISTED", "INTERVIEW")


# ---- helpers ------------------------------------------------------------------------------------------
def _iso(dt: datetime | None) -> str | None:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z") if dt else None


def _build(
    iv: Interview,
    student_id: uuid.UUID,
    student_name: str,
    internship_id: uuid.UUID,
    internship_title: str,
    company_name: str,
    viewer: User,
) -> s.Interview:
    data: dict[str, Any] = {
        "id": iv.id,
        "application_id": iv.application_id,
        "scheduled_at": iv.scheduled_at,
        "duration_minutes": iv.duration_minutes,
        "mode": iv.mode,
        "location": iv.location,
        "meeting_link": iv.meeting_link,
        "interviewer_name": iv.interviewer_name,
        "interviewer_email": iv.interviewer_email,
        "status": iv.status,
        "result": iv.result,
        "score": iv.score,
        "feedback_for_student": iv.feedback_for_student,
        "cancel_reason": iv.cancel_reason,
        "reschedule_count": iv.reschedule_count,
        "student": s.StudentRef(id=student_id, full_name=student_name),
        "internship": s.InterviewInternshipRef(id=internship_id, title=internship_title, company_name=company_name),
        "created_at": iv.created_at,
    }
    if viewer.role == "STUDENT":
        # internal comments are never exposed; feedback is released only once the interview is completed
        if iv.status != "COMPLETED":
            data["feedback_for_student"] = None
    else:
        data["comments"] = iv.comments
    return s.Interview(**data)


def _from_row(row: Any, viewer: User) -> s.Interview:
    return _build(
        row[0], row.student_id, row.student_name, row.internship_id, row.internship_title, row.company_name, viewer
    )


def _email_context(
    iv: Interview, student: User, internship: Internship, company: Company, **extra: Any
) -> dict[str, Any]:
    return {
        "interview_id": str(iv.id),
        "student_name": student.full_name,
        "internship_title": internship.title,
        "company_name": company.name,
        "scheduled_at": _iso(iv.scheduled_at),
        "ends_at": _iso(iv.scheduled_at + timedelta(minutes=iv.duration_minutes)),
        "duration_minutes": iv.duration_minutes,
        "mode": iv.mode,
        "location": iv.location,
        "meeting_link": iv.meeting_link,
        "interviewer_name": iv.interviewer_name,
        "interviewer_email": iv.interviewer_email,
        "link": f"{settings.FRONTEND_URL}/student/interviews",
        **extra,
    }


def _staff_link(user: User) -> str:
    return "/company/interviews" if user.role == "COMPANY" else "/faculty/interviews"


async def _notify_interviewer(
    session: AsyncSession, iv: Interview, actor: User, title: str, body: str, data: dict[str, Any]
) -> None:
    if iv.interviewer_user_id and iv.interviewer_user_id != actor.id:
        interviewer = await repo.get_user(session, iv.interviewer_user_id)
        if interviewer is not None:
            notify(session, interviewer.id, "INTERVIEW_SCHEDULED", title, body, _staff_link(interviewer), data)


def _check_notice_and_deadline(scheduled_at: datetime, duration_minutes: int, internship: Internship) -> None:
    # R1: at least 24h notice
    if scheduled_at < utcnow() + NOTICE:
        raise unprocessable(
            "Interviews must be scheduled at least 24 hours in advance",
            "INTERVIEW_NOTICE_TOO_SHORT",
            [{"field": "scheduled_at", "message": "Must be at least 24 hours from now"}],
        )
    # R2: interview must end before the internship application deadline (our reading of the spec)
    if scheduled_at + timedelta(minutes=duration_minutes) > internship.application_deadline:
        raise unprocessable(
            "The interview must end before the application deadline of the internship",
            "INTERVIEW_AFTER_DEADLINE",
            [{"field": "scheduled_at", "message": "Must end on or before the application deadline"}],
        )


async def _check_overlap(
    session: AsyncSession, student_id: uuid.UUID, start: datetime, minutes: int, exclude: uuid.UUID | None = None
) -> None:
    # R4: no overlap with another active interview of the same student
    if await repo.has_overlap(session, student_id, start, start + timedelta(minutes=minutes), exclude):
        raise conflict("The student already has an interview at this time", "INTERVIEW_CONFLICT")


async def _system_transition(
    session: AsyncSession, application: Application, to_status: str, actor: User, note: str
) -> None:
    """SHORTLISTED <-> INTERVIEW through the WP3b state machine (system transition)."""
    try:
        from app.modules.applications.state_machine import transition_application
    except ImportError:  # pragma: no cover - state machine not landed yet; keep the invariant locally
        from_status = application.status
        application.status = to_status
        application.status_changed_at = utcnow()
        session.add(
            ApplicationStatusHistory(
                application_id=application.id,
                from_status=from_status,
                to_status=to_status,
                changed_by=actor.id,
                note=note,
            )
        )
        await session.flush()
        return
    await transition_application(session, application.id, to_status, actor, note=note, system=True)
    await session.refresh(application)


# ---- reads --------------------------------------------------------------------------------------------
async def list_interviews(
    session: AsyncSession,
    user: User,
    params: PageParams,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    status: str | None,
    application_id: uuid.UUID | None,
) -> dict[str, Any]:
    stmt = repo.base_select().where(await repo.scope_clause(session, user))
    if date_from is not None:
        stmt = stmt.where(Interview.scheduled_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Interview.scheduled_at <= date_to)
    if status:
        stmt = stmt.where(Interview.status == status)
    if application_id is not None:
        stmt = stmt.where(Interview.application_id == application_id)
    stmt = stmt.order_by(Interview.scheduled_at.asc(), Interview.id.asc())
    rows, total = await paginate(session, stmt, params, scalars=False)
    return make_page([_from_row(r, user) for r in rows], total, params)


async def get_interview(session: AsyncSession, user: User, interview_id: uuid.UUID) -> s.Interview:
    row = await repo.get_scoped_row(session, user, interview_id)
    if row is None:
        raise not_found("Interview not found")
    return _from_row(row, user)


async def _get_manageable(
    session: AsyncSession, user: User, interview_id: uuid.UUID, *, allow_interviewer: bool = False
) -> tuple[Interview, Application, Internship, Company, User]:
    """Locks and returns the interview + context. 404 outside scope, 403 when visible but not allowed."""
    row = await repo.get_scoped_row(session, user, interview_id)
    if row is None:
        raise not_found("Interview not found")
    iv = await repo.get_for_update(session, interview_id)
    if iv is None:
        raise not_found("Interview not found")
    ctx = await repo.get_application_ctx(session, iv.application_id, for_update=True)
    if ctx is None:
        raise not_found("Interview not found")
    application, internship, company, student = ctx
    allowed = await can_manage_internship(session, user, internship)
    if not allowed and allow_interviewer and iv.interviewer_user_id == user.id:
        allowed = True
    if not allowed:
        raise forbidden()
    return iv, application, internship, company, student


# ---- writes -------------------------------------------------------------------------------------------
async def create_interview(session: AsyncSession, actor: User, body: s.InterviewCreateRequest) -> s.Interview:
    ctx = await repo.get_application_ctx(session, body.application_id, for_update=True)
    if ctx is None:
        raise not_found("Application not found")
    application, internship, company, student = ctx
    if not await can_manage_internship(session, actor, internship):
        raise not_found("Application not found")

    # R3: only SHORTLISTED / INTERVIEW applications can be scheduled
    if application.status not in SCHEDULABLE_APPLICATION_STATUSES:
        raise conflict(
            f"Cannot schedule an interview for an application in status {application.status}",
            "INVALID_STATUS_TRANSITION",
        )
    _check_notice_and_deadline(body.scheduled_at, body.duration_minutes, internship)

    if body.interviewer_user_id is not None:
        interviewer = await repo.get_user(session, body.interviewer_user_id)
        if interviewer is None or interviewer.role not in ("ADMIN", "FACULTY", "COMPANY") or not interviewer.is_active:
            raise unprocessable(
                "Interviewer must be an active staff user",
                details=[{"field": "interviewer_user_id", "message": "Unknown or ineligible user"}],
            )

    await repo.lock_student(session, application.student_id)
    await _check_overlap(session, application.student_id, body.scheduled_at, body.duration_minutes)

    iv = Interview(
        application_id=application.id,
        scheduled_by=actor.id,
        scheduled_at=body.scheduled_at,
        duration_minutes=body.duration_minutes,
        mode=body.mode.value,
        location=body.location,
        meeting_link=body.meeting_link,
        interviewer_name=body.interviewer_name,
        interviewer_email=body.interviewer_email,
        interviewer_user_id=body.interviewer_user_id,
        status="SCHEDULED",
        result="PENDING",
        reschedule_count=0,
    )
    session.add(iv)
    await session.flush()

    if application.status == "SHORTLISTED":
        await _system_transition(session, application, "INTERVIEW", actor, "Interview scheduled")

    when = _iso(iv.scheduled_at)
    data = {"interview_id": str(iv.id), "application_id": str(application.id)}
    notify(
        session,
        application.student_id,
        "INTERVIEW_SCHEDULED",
        "Interview scheduled",
        f"{company.name} scheduled an interview for {internship.title} on {when}.",
        "/student/interviews",
        data,
    )
    queue_email(session, "interview_scheduled", student.email, _email_context(iv, student, internship, company))
    await _notify_interviewer(
        session,
        iv,
        actor,
        "Interview assigned to you",
        f"Interview with {student.full_name} for {internship.title} on {when}.",
        data,
    )
    audit(
        session,
        actor,
        "interview.create",
        "interview",
        iv.id,
        after={"application_id": str(application.id), "scheduled_at": when, "mode": iv.mode},
    )
    return _build(iv, student.id, student.full_name, internship.id, internship.title, company.name, actor)


async def reschedule_interview(
    session: AsyncSession, actor: User, interview_id: uuid.UUID, body: s.InterviewRescheduleRequest
) -> s.Interview:
    iv, application, internship, company, student = await _get_manageable(session, actor, interview_id)
    if iv.status not in repo.ACTIVE_STATUSES:
        raise conflict(f"Cannot reschedule an interview in status {iv.status}", "INVALID_STATUS_TRANSITION")
    if application.status not in SCHEDULABLE_APPLICATION_STATUSES:
        raise conflict(
            f"Cannot reschedule: application is {application.status}", "INVALID_STATUS_TRANSITION"
        )
    minutes = body.duration_minutes or iv.duration_minutes
    _check_notice_and_deadline(body.scheduled_at, minutes, internship)
    await repo.lock_student(session, application.student_id)
    await _check_overlap(session, application.student_id, body.scheduled_at, minutes, exclude=iv.id)

    before = {"scheduled_at": _iso(iv.scheduled_at), "duration_minutes": iv.duration_minutes}
    iv.scheduled_at = body.scheduled_at
    iv.duration_minutes = minutes
    iv.status = "RESCHEDULED"
    iv.reschedule_count = (iv.reschedule_count or 0) + 1
    iv.reminder_sent_at = None
    await session.flush()

    when = _iso(iv.scheduled_at)
    data = {"interview_id": str(iv.id), "application_id": str(application.id), "reason": body.reason}
    notify(
        session,
        application.student_id,
        "INTERVIEW_RESCHEDULED",
        "Interview rescheduled",
        f"Your interview for {internship.title} was moved to {when}. Reason: {body.reason}",
        "/student/interviews",
        data,
    )
    queue_email(
        session,
        "interview_rescheduled",
        student.email,
        _email_context(iv, student, internship, company, reason=body.reason, previous_scheduled_at=before["scheduled_at"]),
    )
    await _notify_interviewer(
        session,
        iv,
        actor,
        "Interview rescheduled",
        f"Interview with {student.full_name} was moved to {when}.",
        data,
    )
    audit(
        session,
        actor,
        "interview.reschedule",
        "interview",
        iv.id,
        before=before,
        after={"scheduled_at": when, "duration_minutes": iv.duration_minutes, "reason": body.reason},
    )
    return _build(iv, student.id, student.full_name, internship.id, internship.title, company.name, actor)


async def cancel_interview(
    session: AsyncSession, actor: User, interview_id: uuid.UUID, reason: str
) -> s.Interview:
    iv, application, internship, company, student = await _get_manageable(session, actor, interview_id)
    if iv.status not in repo.ACTIVE_STATUSES:
        raise conflict(f"Cannot cancel an interview in status {iv.status}", "INVALID_STATUS_TRANSITION")
    previous = iv.status
    iv.status = "CANCELLED"
    iv.cancel_reason = reason
    await session.flush()

    # last active interview cancelled: INTERVIEW -> SHORTLISTED
    if application.status == "INTERVIEW" and await repo.count_active(session, application.id) == 0:
        await _system_transition(session, application, "SHORTLISTED", actor, "Interview cancelled")

    data = {"interview_id": str(iv.id), "application_id": str(application.id), "reason": reason}
    notify(
        session,
        application.student_id,
        "INTERVIEW_CANCELLED",
        "Interview cancelled",
        f"Your interview for {internship.title} was cancelled. Reason: {reason}",
        "/student/interviews",
        data,
    )
    queue_email(
        session, "interview_cancelled", student.email, _email_context(iv, student, internship, company, reason=reason)
    )
    await _notify_interviewer(
        session, iv, actor, "Interview cancelled", f"Interview with {student.full_name} was cancelled.", data
    )
    audit(
        session,
        actor,
        "interview.cancel",
        "interview",
        iv.id,
        before={"status": previous},
        after={"status": "CANCELLED", "reason": reason},
    )
    return _build(iv, student.id, student.full_name, internship.id, internship.title, company.name, actor)


async def record_result(
    session: AsyncSession, actor: User, interview_id: uuid.UUID, body: s.InterviewResultRequest
) -> s.Interview:
    iv, application, internship, company, student = await _get_manageable(
        session, actor, interview_id, allow_interviewer=True
    )
    if iv.status not in repo.ACTIVE_STATUSES:
        raise conflict(f"Cannot record a result for an interview in status {iv.status}", "INVALID_STATUS_TRANSITION")
    if iv.scheduled_at > utcnow() and actor.role != "ADMIN":
        raise conflict("The interview has not taken place yet", "CONFLICT")

    iv.status = body.status.value
    iv.result = body.result.value
    iv.score = body.score
    iv.comments = body.comments
    iv.feedback_for_student = body.feedback_for_student
    await session.flush()

    if iv.status == "COMPLETED":
        notify(
            session,
            application.student_id,
            "INTERVIEW_COMPLETED",
            "Interview feedback available",
            f"Your interview for {internship.title} has been completed.",
            "/student/interviews",
            {"interview_id": str(iv.id), "application_id": str(application.id)},
        )
    audit(
        session,
        actor,
        "interview.result",
        "interview",
        iv.id,
        after={"status": iv.status, "result": iv.result, "score": iv.score},
    )
    return _build(iv, student.id, student.full_name, internship.id, internship.title, company.name, actor)
