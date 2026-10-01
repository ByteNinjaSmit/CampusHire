"""Interview queries. Services never build SQL; routers never touch the session."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Integer, Select, and_, cast, func, literal_column, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import owned_internship_ids
from app.modules.applications.models import Application
from app.modules.companies.models import Company
from app.modules.internships.models import Internship
from app.modules.interviews.models import Interview
from app.modules.users.models import User

ACTIVE_STATUSES = ("SCHEDULED", "RESCHEDULED")


def base_select() -> Select[Any]:
    """Interview + display columns (student, internship, company)."""
    return (
        select(
            Interview,
            Application.student_id.label("student_id"),
            User.full_name.label("student_name"),
            Internship.id.label("internship_id"),
            Internship.title.label("internship_title"),
            Company.name.label("company_name"),
        )
        .join(Application, Application.id == Interview.application_id)
        .join(Internship, Internship.id == Application.internship_id)
        .join(Company, Company.id == Internship.company_id)
        .join(User, User.id == Application.student_id)
    )


async def scope_clause(session: AsyncSession, user: User) -> Any:
    """Rows visible to ``user``: student own; staff own internships or interviewer; admin all."""
    if user.role == "ADMIN":
        return true()
    if user.role == "STUDENT":
        return Application.student_id == user.id
    owned = await owned_internship_ids(session, user)
    return or_(Application.internship_id.in_(owned), Interview.interviewer_user_id == user.id)


async def get_scoped_row(session: AsyncSession, user: User, interview_id: uuid.UUID) -> Any | None:
    clause = await scope_clause(session, user)
    stmt = base_select().where(Interview.id == interview_id, clause)
    return (await session.execute(stmt)).first()


async def get_for_update(session: AsyncSession, interview_id: uuid.UUID) -> Interview | None:
    stmt = (
        select(Interview)
        .where(Interview.id == interview_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_application_ctx(
    session: AsyncSession, application_id: uuid.UUID, *, for_update: bool = False
) -> tuple[Application, Internship, Company, User] | None:
    stmt = (
        select(Application, Internship, Company, User)
        .join(Internship, Internship.id == Application.internship_id)
        .join(Company, Company.id == Internship.company_id)
        .join(User, User.id == Application.student_id)
        .where(Application.id == application_id)
    )
    if for_update:
        stmt = stmt.with_for_update(of=Application).execution_options(populate_existing=True)
    row = (await session.execute(stmt)).first()
    return (row[0], row[1], row[2], row[3]) if row else None


async def lock_student(session: AsyncSession, student_id: uuid.UUID) -> None:
    """Serialise interview scheduling per student so the overlap check (R4) cannot race."""
    await session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(str(student_id), 0))))


async def has_overlap(
    session: AsyncSession,
    student_id: uuid.UUID,
    start: datetime,
    end: datetime,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    ends_at = Interview.scheduled_at + cast(Interview.duration_minutes, Integer) * literal_column(
        "interval '1 minute'"
    )
    conds = [
        Application.student_id == student_id,
        Interview.status.in_(ACTIVE_STATUSES),
        Interview.scheduled_at < end,
        ends_at > start,
    ]
    if exclude_id is not None:
        conds.append(Interview.id != exclude_id)
    stmt = (
        select(func.count())
        .select_from(Interview)
        .join(Application, Application.id == Interview.application_id)
        .where(and_(*conds))
    )
    return (await session.execute(stmt)).scalar_one() > 0


async def count_active(session: AsyncSession, application_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(Interview)
        .where(Interview.application_id == application_id, Interview.status.in_(ACTIVE_STATUSES))
    )
    return int((await session.execute(stmt)).scalar_one())


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
