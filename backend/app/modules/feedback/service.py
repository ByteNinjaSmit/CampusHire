"""Feedback: student -> company, company -> student, faculty, and system feedback (plan 3.11 / 4.4)."""

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import utcnow
from app.core.errors import AppError, conflict, not_found, unprocessable
from app.core.pagination import PageParams, make_page, paginate
from app.core.permissions import can_manage_internship
from app.core.side_effects import audit, notify
from app.modules.feedback import repository as repo
from app.modules.feedback import schemas as s
from app.modules.feedback.models import (
    CompanyFeedback,
    FacultyFeedback,
    FeedbackActionItem,
    StudentFeedback,
    SystemFeedback,
)
from app.modules.users.models import User

# ======================================================================================================
# student feedback
# ======================================================================================================


def _student_feedback_out(row: Any, viewer: User) -> s.StudentFeedback:
    fb: StudentFeedback = row[0]
    reveal = (not fb.is_anonymous) or viewer.role == "ADMIN" or viewer.id == fb.student_id
    return s.StudentFeedback(
        id=fb.id,
        application_id=fb.application_id,
        company_culture=fb.company_culture,
        mentorship=fb.mentorship,
        technical_learning=fb.technical_learning,
        work_environment=fb.work_environment,
        overall=fb.overall,
        comments=fb.comments,
        suggestions=fb.suggestions,
        is_anonymous=fb.is_anonymous,
        student_name=row.student_name if reveal else None,
        company=s.CompanyRef(id=fb.company_id, name=row.company_name),
        internship=s.InternshipRef(id=fb.internship_id, title=row.internship_title),
        response_body=fb.response_body,
        responded_by_name=row.responder_name,
        responded_at=fb.responded_at,
        created_at=fb.created_at,
    )


async def create_student_feedback(
    session: AsyncSession, actor: User, body: s.StudentFeedbackCreateRequest
) -> s.StudentFeedback:
    ctx = await repo.application_ctx(session, body.application_id)
    if ctx is None or ctx[0].student_id != actor.id:
        raise not_found("Application not found")
    application, internship, company, student = ctx
    completed = application.completed_at is not None or internship.end_date <= datetime.now(UTC).date()
    if application.status != "ACCEPTED" or not completed:
        raise conflict(
            "Feedback can only be given for an accepted internship that has been completed", "CONFLICT"
        )
    if await repo.student_feedback_exists(session, application.id):
        raise AppError(409, "DUPLICATE_FEEDBACK", "Feedback has already been submitted for this application")

    fb = StudentFeedback(
        application_id=application.id,
        student_id=actor.id,
        company_id=company.id,
        internship_id=internship.id,
        company_culture=body.company_culture,
        mentorship=body.mentorship,
        technical_learning=body.technical_learning,
        work_environment=body.work_environment,
        overall=body.overall,
        comments=body.comments,
        suggestions=body.suggestions,
        is_anonymous=body.is_anonymous,
    )
    session.add(fb)
    await session.flush()
    who = "A student" if body.is_anonymous else student.full_name
    notify(
        session,
        internship.posted_by,
        "FEEDBACK_RECEIVED",
        "New student feedback",
        f"{who} left feedback on {internship.title} (overall {body.overall}/5).",
        "/faculty/feedback" if internship.posted_by != actor.id else None,
        {"feedback_id": str(fb.id), "internship_id": str(internship.id)},
    )
    audit(
        session,
        actor,
        "feedback.student.create",
        "student_feedback",
        fb.id,
        after={"application_id": str(application.id), "overall": fb.overall},
    )
    row = await repo.get_student_feedback_row(session, fb.id, await repo.student_feedback_scope(session, actor))
    return _student_feedback_out(row, actor)


async def list_student_feedback(
    session: AsyncSession,
    user: User,
    params: PageParams,
    *,
    company_id: uuid.UUID | None,
    internship_id: uuid.UUID | None,
) -> dict[str, Any]:
    stmt = repo.student_feedback_select().where(await repo.student_feedback_scope(session, user))
    if company_id is not None:
        stmt = stmt.where(StudentFeedback.company_id == company_id)
    if internship_id is not None:
        stmt = stmt.where(StudentFeedback.internship_id == internship_id)
    stmt = stmt.order_by(StudentFeedback.created_at.desc(), StudentFeedback.id.asc())
    rows, total = await paginate(session, stmt, params, scalars=False)
    return make_page([_student_feedback_out(r, user) for r in rows], total, params)


def _month_key(dt: datetime) -> str:
    dt = dt.astimezone(UTC)
    return f"{dt.year:04d}-{dt.month:02d}"


async def student_feedback_trends(
    session: AsyncSession,
    user: User,
    *,
    company_id: uuid.UUID | None,
    internship_id: uuid.UUID | None,
    months: int,
) -> s.FeedbackTrends:
    now = utcnow()
    keys: list[str] = []
    y, m = now.year, now.month
    for _ in range(months):
        keys.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    keys.reverse()
    first_y, first_m = int(keys[0][:4]), int(keys[0][5:])
    since = datetime(first_y, first_m, 1, tzinfo=UTC)
    rows = await repo.student_feedback_trend_rows(
        session, await repo.student_feedback_scope(session, user), since, company_id, internship_id
    )
    sums: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    counts: dict[str, int] = defaultdict(int)
    for created_at, *vals in rows:
        key = _month_key(created_at)
        counts[key] += 1
        for dim, val in zip(s.DIMENSIONS, vals, strict=True):
            sums[key][dim] += val
    series = [
        s.FeedbackTrendSeries(
            dimension=dim,  # type: ignore[arg-type]
            values=[round(sums[k][dim] / counts[k], 2) if counts[k] else None for k in keys],
        )
        for dim in s.DIMENSIONS
    ]
    return s.FeedbackTrends(months=keys, series=series, counts=[counts[k] for k in keys])


async def respond_to_student_feedback(
    session: AsyncSession, actor: User, feedback_id: uuid.UUID, body: str
) -> s.StudentFeedback:
    scope = await repo.student_feedback_scope(session, actor)
    if await repo.get_student_feedback_row(session, feedback_id, scope) is None:
        raise not_found("Feedback not found")
    fb = await repo.get_student_feedback_for_update(session, feedback_id)
    assert fb is not None
    fb.response_body = body
    fb.responded_by = actor.id
    fb.responded_at = utcnow()
    await session.flush()
    notify(
        session,
        fb.student_id,
        "FEEDBACK_RESPONSE",
        "Your feedback received a response",
        body[:200],
        "/student/feedback",
        {"feedback_id": str(fb.id)},
    )
    audit(session, actor, "feedback.student.respond", "student_feedback", fb.id)
    row = await repo.get_student_feedback_row(session, fb.id, scope)
    return _student_feedback_out(row, actor)


async def company_rating_summaries(session: AsyncSession, company_ids: list[uuid.UUID]) -> dict[uuid.UUID, s.RatingSummary]:
    """Aggregated company ratings from student feedback (helper for the companies module)."""
    aggs = await repo.rating_aggregates(session, company_ids)
    return {cid: s.RatingSummary(**agg) for cid, agg in aggs.items()}


async def company_rating_summary(session: AsyncSession, company_id: uuid.UUID) -> s.RatingSummary:
    return (await company_rating_summaries(session, [company_id]))[company_id]


# ======================================================================================================
# company feedback (company / staff rates a student)
# ======================================================================================================

_COMPANY_DIMS = ("technical_skills", "soft_skills", "punctuality", "responsibility", "teamwork", "learning_ability")


def _company_feedback_out(row: Any) -> s.CompanyFeedback:
    fb: CompanyFeedback = row[0]
    avg = sum(getattr(fb, d) for d in _COMPANY_DIMS) / len(_COMPANY_DIMS)
    return s.CompanyFeedback(
        id=fb.id,
        application_id=fb.application_id,
        technical_skills=fb.technical_skills,
        soft_skills=fb.soft_skills,
        punctuality=fb.punctuality,
        responsibility=fb.responsibility,
        teamwork=fb.teamwork,
        learning_ability=fb.learning_ability,
        strengths=fb.strengths,
        improvements=fb.improvements,
        hire_likelihood=fb.hire_likelihood,
        author_name=row.author_name,
        student=s.Ref(id=row.student_id, full_name=row.student_name),
        internship=s.InternshipRef(id=row.internship_id, title=row.internship_title),
        average=round(avg, 2),
        created_at=fb.created_at,
    )


async def create_company_feedback(
    session: AsyncSession, actor: User, body: s.CompanyFeedbackCreateRequest
) -> s.CompanyFeedback:
    ctx = await repo.application_ctx(session, body.application_id)
    if ctx is None:
        raise not_found("Application not found")
    application, internship, _company, student = ctx
    if not await can_manage_internship(session, actor, internship):
        raise not_found("Application not found")
    if application.status != "ACCEPTED":
        raise conflict("Feedback can only be given for accepted applications", "CONFLICT")
    if await repo.company_feedback_exists(session, application.id, actor.id):
        raise AppError(409, "DUPLICATE_FEEDBACK", "You have already submitted feedback for this application")
    fb = CompanyFeedback(
        application_id=application.id,
        author_id=actor.id,
        technical_skills=body.technical_skills,
        soft_skills=body.soft_skills,
        punctuality=body.punctuality,
        responsibility=body.responsibility,
        teamwork=body.teamwork,
        learning_ability=body.learning_ability,
        strengths=body.strengths,
        improvements=body.improvements,
        hire_likelihood=body.hire_likelihood,
    )
    session.add(fb)
    await session.flush()
    notify(
        session,
        student.id,
        "FEEDBACK_RECEIVED",
        "You received performance feedback",
        f"Feedback on your internship {internship.title} is available.",
        "/student/feedback",
        {"feedback_id": str(fb.id), "application_id": str(application.id)},
    )
    audit(
        session,
        actor,
        "feedback.company.create",
        "company_feedback",
        fb.id,
        after={"application_id": str(application.id), "hire_likelihood": fb.hire_likelihood},
    )
    row = await repo.get_company_feedback_row(session, fb.id)
    return _company_feedback_out(row)


async def list_company_feedback(
    session: AsyncSession,
    user: User,
    params: PageParams,
    *,
    application_id: uuid.UUID | None,
    student_id: uuid.UUID | None,
) -> dict[str, Any]:
    from app.modules.applications.models import Application

    stmt = repo.company_feedback_select().where(await repo.company_feedback_scope(session, user))
    if application_id is not None:
        stmt = stmt.where(CompanyFeedback.application_id == application_id)
    if student_id is not None:
        stmt = stmt.where(Application.student_id == student_id)
    stmt = stmt.order_by(CompanyFeedback.created_at.desc(), CompanyFeedback.id.asc())
    rows, total = await paginate(session, stmt, params, scalars=False)
    return make_page([_company_feedback_out(r) for r in rows], total, params)


# ======================================================================================================
# faculty feedback
# ======================================================================================================


def _faculty_feedback_out(row: Any) -> s.FacultyFeedback:
    fb: FacultyFeedback = row[0]
    return s.FacultyFeedback(
        id=fb.id,
        internship_id=fb.internship_id,
        application_id=fb.application_id,
        course_suitability=fb.course_suitability,
        learning_outcomes=fb.learning_outcomes,
        internship_quality=fb.internship_quality,
        suggestions=fb.suggestions,
        comments=fb.comments,
        faculty_name=row.faculty_name,
        internship_title=row.internship_title,
        created_at=fb.created_at,
    )


async def create_faculty_feedback(
    session: AsyncSession, actor: User, body: s.FacultyFeedbackCreateRequest
) -> s.FacultyFeedback:
    found = await repo.get_internship_with_company(session, body.internship_id)
    if found is None:
        raise not_found("Internship not found")
    internship, _company = found
    if not await can_manage_internship(session, actor, internship):
        raise not_found("Internship not found")
    if body.application_id is not None:
        ctx = await repo.application_ctx(session, body.application_id)
        if ctx is None or ctx[0].internship_id != internship.id:
            raise unprocessable(
                "The application does not belong to this internship",
                details=[{"field": "application_id", "message": "Does not belong to the internship"}],
            )
    fb = FacultyFeedback(
        internship_id=internship.id,
        application_id=body.application_id,
        faculty_id=actor.id,
        course_suitability=body.course_suitability,
        learning_outcomes=body.learning_outcomes,
        internship_quality=body.internship_quality,
        suggestions=body.suggestions,
        comments=body.comments,
    )
    session.add(fb)
    await session.flush()
    audit(
        session,
        actor,
        "feedback.faculty.create",
        "faculty_feedback",
        fb.id,
        after={"internship_id": str(internship.id), "internship_quality": fb.internship_quality},
    )
    return _faculty_feedback_out(await repo.get_faculty_feedback_row(session, fb.id))


async def list_faculty_feedback(
    session: AsyncSession, user: User, params: PageParams, *, internship_id: uuid.UUID | None
) -> dict[str, Any]:
    stmt = repo.faculty_feedback_select().where(await repo.faculty_feedback_scope(session, user))
    if internship_id is not None:
        stmt = stmt.where(FacultyFeedback.internship_id == internship_id)
    stmt = stmt.order_by(FacultyFeedback.created_at.desc(), FacultyFeedback.id.asc())
    rows, total = await paginate(session, stmt, params, scalars=False)
    return make_page([_faculty_feedback_out(r) for r in rows], total, params)


# ======================================================================================================
# system feedback + triage
# ======================================================================================================


def _action_item_out(item: FeedbackActionItem) -> s.ActionItem:
    assignee = item.assignee
    return s.ActionItem(
        id=item.id,
        title=item.title,
        assignee=s.Ref(id=assignee.id, full_name=assignee.full_name) if assignee else None,
        status=item.status,  # type: ignore[arg-type]
        due_date=item.due_date,
        created_at=item.created_at,
    )


def _system_out(fb: SystemFeedback, viewer: User) -> s.SystemFeedback:
    items = sorted(fb.action_items, key=lambda i: i.created_at)
    return s.SystemFeedback(
        id=fb.id,
        type=fb.type,  # type: ignore[arg-type]
        title=fb.title,
        description=fb.description,
        page_url=fb.page_url,
        severity=fb.severity,  # type: ignore[arg-type]
        user=s.SystemFeedbackUser(id=fb.user.id, full_name=fb.user.full_name, role=fb.user.role),  # type: ignore[arg-type]
        status=fb.status,  # type: ignore[arg-type]
        priority=fb.priority,  # type: ignore[arg-type]
        admin_notes=fb.admin_notes if viewer.role == "ADMIN" else None,
        action_items=[_action_item_out(i) for i in items],
        created_at=fb.created_at,
    )


async def create_system_feedback(
    session: AsyncSession, actor: User, body: s.SystemFeedbackCreateRequest
) -> s.SystemFeedback:
    fb = SystemFeedback(
        user_id=actor.id,
        type=body.type,
        title=body.title,
        description=body.description,
        page_url=body.page_url,
        severity=body.severity if body.type == "BUG" else None,
        status="NEW",
    )
    session.add(fb)
    await session.flush()
    audit(session, actor, "feedback.system.create", "system_feedback", fb.id, after={"type": fb.type})
    loaded = await repo.get_system_feedback(session, fb.id, fresh=True)
    assert loaded is not None
    return _system_out(loaded, actor)


async def list_system_feedback(
    session: AsyncSession, user: User, params: PageParams, *, type_: str | None, status: str | None
) -> dict[str, Any]:
    stmt = repo.system_feedback_select()
    if user.role != "ADMIN":
        stmt = stmt.where(SystemFeedback.user_id == user.id)
    if type_:
        stmt = stmt.where(SystemFeedback.type == type_)
    if status:
        stmt = stmt.where(SystemFeedback.status == status)
    stmt = stmt.order_by(SystemFeedback.created_at.desc(), SystemFeedback.id.asc())
    rows, total = await paginate(session, stmt, params)
    return make_page([_system_out(r, user) for r in rows], total, params)


async def system_feedback_summary(session: AsyncSession) -> s.SystemFeedbackSummary:
    today = utcnow().date()
    start = today - timedelta(days=29)
    since = datetime(start.year, start.month, start.day, tzinfo=UTC)
    counts = await repo.daily_counts(session, since)
    return s.SystemFeedbackSummary(
        by_type=await repo.count_by(session, SystemFeedback.type),
        by_status=await repo.count_by(session, SystemFeedback.status),
        last_30_days=[
            s.DayCount(date=d, count=counts.get(d, 0)) for d in (start + timedelta(days=i) for i in range(30))
        ],
        open_action_items=await repo.open_action_items(session),
    )


async def update_system_feedback(
    session: AsyncSession, actor: User, feedback_id: uuid.UUID, body: s.SystemFeedbackUpdateRequest
) -> s.SystemFeedback:
    fb = await repo.get_system_feedback(session, feedback_id, fresh=True)
    if fb is None:
        raise not_found("Feedback not found")
    fields = body.model_fields_set
    before = {"status": fb.status, "priority": fb.priority}
    status_changed = False
    if "status" in fields and body.status is not None:
        status_changed = body.status != fb.status
        fb.status = body.status
    if "priority" in fields:
        fb.priority = body.priority
    if "admin_notes" in fields:
        fb.admin_notes = body.admin_notes
    await session.flush()
    if status_changed and fb.user_id != actor.id:
        notify(
            session,
            fb.user_id,
            "SYSTEM",
            "Your feedback was updated",
            f'"{fb.title}" is now {fb.status.replace("_", " ").lower()}.',
            "/feedback/system",
            {"feedback_id": str(fb.id), "status": fb.status},
        )
    audit(
        session,
        actor,
        "feedback.system.update",
        "system_feedback",
        fb.id,
        before=before,
        after={"status": fb.status, "priority": fb.priority},
    )
    return _system_out(fb, actor)


async def _check_assignee(session: AsyncSession, assignee_id: uuid.UUID | None) -> None:
    if assignee_id is None:
        return
    user = await repo.get_user(session, assignee_id)
    if user is None or not user.is_active:
        raise unprocessable(
            "Unknown assignee", details=[{"field": "assignee_id", "message": "User not found or inactive"}]
        )


async def add_action_item(
    session: AsyncSession, actor: User, feedback_id: uuid.UUID, body: s.ActionItemCreateRequest
) -> s.ActionItem:
    fb = await repo.get_system_feedback(session, feedback_id)
    if fb is None:
        raise not_found("Feedback not found")
    await _check_assignee(session, body.assignee_id)
    item = FeedbackActionItem(
        system_feedback_id=fb.id,
        title=body.title,
        assignee_id=body.assignee_id,
        due_date=body.due_date,
        status="OPEN",
    )
    session.add(item)
    await session.flush()
    if body.assignee_id and body.assignee_id != actor.id:
        notify(
            session,
            body.assignee_id,
            "SYSTEM",
            "New action item assigned",
            body.title,
            None,
            {"action_item_id": str(item.id), "feedback_id": str(fb.id)},
        )
    audit(
        session,
        actor,
        "feedback.action_item.create",
        "feedback_action_item",
        item.id,
        after={"system_feedback_id": str(fb.id), "title": item.title},
    )
    loaded = await repo.get_action_item(session, item.id)
    assert loaded is not None
    return _action_item_out(loaded)


async def update_action_item(
    session: AsyncSession, actor: User, item_id: uuid.UUID, body: s.ActionItemUpdateRequest
) -> s.ActionItem:
    item = await repo.get_action_item(session, item_id)
    if item is None:
        raise not_found("Action item not found")
    fields = body.model_fields_set
    before = {"status": item.status, "title": item.title}
    if "status" in fields and body.status is not None:
        item.status = body.status
    if "title" in fields and body.title is not None:
        item.title = body.title
    if "due_date" in fields:
        item.due_date = body.due_date
    if "assignee_id" in fields:
        await _check_assignee(session, body.assignee_id)
        item.assignee_id = body.assignee_id
    await session.flush()
    audit(
        session,
        actor,
        "feedback.action_item.update",
        "feedback_action_item",
        item.id,
        before=before,
        after={"status": item.status, "title": item.title},
    )
    loaded = await repo.get_action_item(session, item.id)
    assert loaded is not None
    return _action_item_out(loaded)

