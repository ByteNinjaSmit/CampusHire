"""Feedback queries."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, exists, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.core.permissions import owned_internship_ids
from app.modules.applications.models import Application
from app.modules.companies.models import Company
from app.modules.feedback.models import (
    CompanyFeedback,
    FacultyFeedback,
    FeedbackActionItem,
    StudentFeedback,
    SystemFeedback,
)
from app.modules.internships.models import Internship
from app.modules.users.models import User

# ---- shared lookups -----------------------------------------------------------------------------------


async def application_ctx(
    session: AsyncSession, application_id: uuid.UUID
) -> tuple[Application, Internship, Company, User] | None:
    stmt = (
        select(Application, Internship, Company, User)
        .join(Internship, Internship.id == Application.internship_id)
        .join(Company, Company.id == Internship.company_id)
        .join(User, User.id == Application.student_id)
        .where(Application.id == application_id)
    )
    row = (await session.execute(stmt)).first()
    return (row[0], row[1], row[2], row[3]) if row else None


async def get_internship_with_company(
    session: AsyncSession, internship_id: uuid.UUID
) -> tuple[Internship, Company] | None:
    stmt = (
        select(Internship, Company)
        .join(Company, Company.id == Internship.company_id)
        .where(Internship.id == internship_id)
    )
    row = (await session.execute(stmt)).first()
    return (row[0], row[1]) if row else None


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()


# ---- student feedback ---------------------------------------------------------------------------------


def student_feedback_select() -> Select[Any]:
    responder = aliased(User)
    return (
        select(
            StudentFeedback,
            User.full_name.label("student_name"),
            Company.name.label("company_name"),
            Internship.title.label("internship_title"),
            responder.full_name.label("responder_name"),
        )
        .join(User, User.id == StudentFeedback.student_id)
        .join(Company, Company.id == StudentFeedback.company_id)
        .join(Internship, Internship.id == StudentFeedback.internship_id)
        .outerjoin(responder, responder.id == StudentFeedback.responded_by)
    )


async def student_feedback_scope(session: AsyncSession, user: User) -> Any:
    if user.role == "ADMIN":
        return true()
    if user.role == "STUDENT":
        return StudentFeedback.student_id == user.id
    owned = await owned_internship_ids(session, user)
    return StudentFeedback.internship_id.in_(owned)


async def student_feedback_exists(session: AsyncSession, application_id: uuid.UUID) -> bool:
    return bool(await session.scalar(select(exists().where(StudentFeedback.application_id == application_id))))


async def get_student_feedback_row(session: AsyncSession, feedback_id: uuid.UUID, scope: Any) -> Any | None:
    stmt = student_feedback_select().where(StudentFeedback.id == feedback_id, scope)
    return (await session.execute(stmt)).first()


async def get_student_feedback_for_update(session: AsyncSession, feedback_id: uuid.UUID) -> StudentFeedback | None:
    stmt = (
        select(StudentFeedback)
        .where(StudentFeedback.id == feedback_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def student_feedback_trend_rows(
    session: AsyncSession,
    scope: Any,
    since: datetime,
    company_id: uuid.UUID | None,
    internship_id: uuid.UUID | None,
) -> list[Any]:
    stmt = select(
        StudentFeedback.created_at,
        StudentFeedback.overall,
        StudentFeedback.company_culture,
        StudentFeedback.mentorship,
        StudentFeedback.technical_learning,
        StudentFeedback.work_environment,
    ).where(StudentFeedback.created_at >= since, scope)
    if company_id is not None:
        stmt = stmt.where(StudentFeedback.company_id == company_id)
    if internship_id is not None:
        stmt = stmt.where(StudentFeedback.internship_id == internship_id)
    return list((await session.execute(stmt)).all())


async def rating_aggregates(session: AsyncSession, company_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, Any]]:
    """Per company: count, dimension averages and the distribution of ``overall`` (1..5)."""
    out: dict[uuid.UUID, dict[str, Any]] = {
        cid: {
            "count": 0,
            "overall": None,
            "company_culture": None,
            "mentorship": None,
            "technical_learning": None,
            "work_environment": None,
            "distribution": {str(i): 0 for i in range(1, 6)},
        }
        for cid in company_ids
    }
    if not company_ids:
        return out
    stmt = (
        select(
            StudentFeedback.company_id,
            func.count(),
            func.avg(StudentFeedback.overall),
            func.avg(StudentFeedback.company_culture),
            func.avg(StudentFeedback.mentorship),
            func.avg(StudentFeedback.technical_learning),
            func.avg(StudentFeedback.work_environment),
        )
        .where(StudentFeedback.company_id.in_(company_ids))
        .group_by(StudentFeedback.company_id)
    )
    for cid, cnt, ov, cu, me, te, we in (await session.execute(stmt)).all():
        agg = out[cid]
        agg["count"] = int(cnt)
        for key, val in (
            ("overall", ov),
            ("company_culture", cu),
            ("mentorship", me),
            ("technical_learning", te),
            ("work_environment", we),
        ):
            agg[key] = round(float(val), 2) if val is not None else None
    dist = await session.execute(
        select(StudentFeedback.company_id, StudentFeedback.overall, func.count())
        .where(StudentFeedback.company_id.in_(company_ids))
        .group_by(StudentFeedback.company_id, StudentFeedback.overall)
    )
    for cid, rating, cnt in dist.all():
        out[cid]["distribution"][str(rating)] = int(cnt)
    return out


# ---- company feedback ---------------------------------------------------------------------------------


def company_feedback_select() -> Select[Any]:
    student = aliased(User)
    author = aliased(User)
    return (
        select(
            CompanyFeedback,
            author.full_name.label("author_name"),
            student.id.label("student_id"),
            student.full_name.label("student_name"),
            Internship.id.label("internship_id"),
            Internship.title.label("internship_title"),
        )
        .join(author, author.id == CompanyFeedback.author_id)
        .join(Application, Application.id == CompanyFeedback.application_id)
        .join(student, student.id == Application.student_id)
        .join(Internship, Internship.id == Application.internship_id)
    )


async def company_feedback_scope(session: AsyncSession, user: User) -> Any:
    if user.role == "ADMIN":
        return true()
    if user.role == "STUDENT":
        return Application.student_id == user.id
    owned = await owned_internship_ids(session, user)
    return Application.internship_id.in_(owned)


async def company_feedback_exists(session: AsyncSession, application_id: uuid.UUID, author_id: uuid.UUID) -> bool:
    return bool(
        await session.scalar(
            select(
                exists().where(
                    CompanyFeedback.application_id == application_id, CompanyFeedback.author_id == author_id
                )
            )
        )
    )


async def get_company_feedback_row(session: AsyncSession, feedback_id: uuid.UUID) -> Any | None:
    return (await session.execute(company_feedback_select().where(CompanyFeedback.id == feedback_id))).first()


# ---- faculty feedback ---------------------------------------------------------------------------------


def faculty_feedback_select() -> Select[Any]:
    return (
        select(FacultyFeedback, User.full_name.label("faculty_name"), Internship.title.label("internship_title"))
        .join(User, User.id == FacultyFeedback.faculty_id)
        .join(Internship, Internship.id == FacultyFeedback.internship_id)
    )


async def faculty_feedback_scope(session: AsyncSession, user: User) -> Any:
    if user.role == "ADMIN":
        return true()
    owned = await owned_internship_ids(session, user)
    return or_(FacultyFeedback.internship_id.in_(owned), FacultyFeedback.faculty_id == user.id)


async def get_faculty_feedback_row(session: AsyncSession, feedback_id: uuid.UUID) -> Any | None:
    return (await session.execute(faculty_feedback_select().where(FacultyFeedback.id == feedback_id))).first()


# ---- system feedback ----------------------------------------------------------------------------------


def system_feedback_select() -> Select[Any]:
    return select(SystemFeedback).options(
        selectinload(SystemFeedback.user),
        selectinload(SystemFeedback.action_items).selectinload(FeedbackActionItem.assignee),
    )


async def get_system_feedback(session: AsyncSession, feedback_id: uuid.UUID, *, fresh: bool = False) -> SystemFeedback | None:
    stmt = system_feedback_select().where(SystemFeedback.id == feedback_id)
    if fresh:
        stmt = stmt.execution_options(populate_existing=True)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_action_item(
    session: AsyncSession, item_id: uuid.UUID
) -> FeedbackActionItem | None:
    stmt = (
        select(FeedbackActionItem)
        .where(FeedbackActionItem.id == item_id)
        .options(selectinload(FeedbackActionItem.assignee))
        .execution_options(populate_existing=True)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def count_by(session: AsyncSession, column: Any) -> dict[str, int]:
    rows = await session.execute(select(column, func.count()).group_by(column))
    return {str(k): int(v) for k, v in rows.all()}


async def daily_counts(session: AsyncSession, since: datetime) -> dict[Any, int]:
    day = func.date(func.timezone("UTC", SystemFeedback.created_at))
    rows = await session.execute(
        select(day, func.count()).where(SystemFeedback.created_at >= since).group_by(day)
    )
    return {d: int(c) for d, c in rows.all()}


async def open_action_items(session: AsyncSession) -> int:
    return int(
        (
            await session.execute(
                select(func.count()).select_from(FeedbackActionItem).where(FeedbackActionItem.status != "DONE")
            )
        ).scalar_one()
    )
