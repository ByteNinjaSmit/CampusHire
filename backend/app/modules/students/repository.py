import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import utcnow
from app.modules.applications.models import Application
from app.modules.companies.models import Company
from app.modules.documents.models import Document
from app.modules.evaluations.models import Evaluation
from app.modules.internships.models import Internship
from app.modules.interviews.models import Interview
from app.modules.students.models import Student
from app.modules.users.models import User

UPCOMING_INTERVIEW_STATUSES = ("SCHEDULED", "RESCHEDULED")


async def get_with_user(session: AsyncSession, student_id: uuid.UUID) -> tuple[Student, User] | None:
    row = (
        await session.execute(
            select(Student, User).join(User, User.id == Student.user_id).where(Student.user_id == student_id)
        )
    ).first()
    return (row[0], row[1]) if row else None


async def get_document(session: AsyncSession, document_id: uuid.UUID | None) -> Document | None:
    if document_id is None:
        return None
    return (
        await session.execute(select(Document).where(Document.id == document_id, Document.deleted_at.is_(None)))
    ).scalar_one_or_none()


def _app_filters(scope: Select[Any] | None) -> list[Any]:
    return [Application.internship_id.in_(scope)] if scope is not None else []


def list_query(
    q: str | None,
    department: str | None,
    gpa_min: float | None,
    gpa_max: float | None,
    scope: Select[Any] | None,
) -> Select[Any]:
    """(Student, User, application_count, placed). ``scope`` = internship ids a FACULTY member owns."""
    app_count = (
        select(func.count())
        .select_from(Application)
        .where(Application.student_id == Student.user_id, *_app_filters(scope))
        .correlate(Student)
        .scalar_subquery()
    )
    placed = exists().where(Application.student_id == Student.user_id, Application.status == "ACCEPTED")
    stmt = (
        select(Student, User, app_count.label("application_count"), placed.label("placed"))
        .join(User, User.id == Student.user_id)
    )
    if scope is not None:
        stmt = stmt.where(exists().where(Application.student_id == Student.user_id, *_app_filters(scope)))
    if q:
        escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(like, escape="\\"),
                User.email.ilike(like, escape="\\"),
                Student.enrollment_no.ilike(like, escape="\\"),
            )
        )
    if department:
        stmt = stmt.where(Student.department == department)
    if gpa_min is not None:
        stmt = stmt.where(Student.gpa >= gpa_min)
    if gpa_max is not None:
        stmt = stmt.where(Student.gpa <= gpa_max)
    return stmt.order_by(User.full_name, Student.user_id)


async def item_row(
    session: AsyncSession, student_id: uuid.UUID, scope: Select[Any] | None
) -> tuple[Student, User, int, bool] | None:
    row = (await session.execute(list_query(None, None, None, None, None).where(Student.user_id == student_id))).first()
    if row is None:
        return None
    count = row[2]
    if scope is not None:
        count = (
            await session.execute(
                select(func.count()).select_from(Application).where(
                    Application.student_id == student_id, *_app_filters(scope)
                )
            )
        ).scalar_one()
    return row[0], row[1], int(count), bool(row[3])


async def has_application_in_scope(session: AsyncSession, student_id: uuid.UUID, scope: Select[Any]) -> bool:
    stmt = select(Application.id).where(Application.student_id == student_id, *_app_filters(scope)).limit(1)
    return (await session.execute(stmt)).first() is not None


async def status_counts(session: AsyncSession, student_id: uuid.UUID, scope: Select[Any] | None) -> dict[str, int]:
    rows = await session.execute(
        select(Application.status, func.count())
        .where(Application.student_id == student_id, *_app_filters(scope))
        .group_by(Application.status)
    )
    return {status: int(n) for status, n in rows.all()}


async def upcoming_interviews(session: AsyncSession, student_id: uuid.UUID, scope: Select[Any] | None) -> int:
    stmt = (
        select(func.count())
        .select_from(Interview)
        .join(Application, Application.id == Interview.application_id)
        .where(
            Application.student_id == student_id,
            Interview.status.in_(UPCOMING_INTERVIEW_STATUSES),
            Interview.scheduled_at > utcnow(),
            *_app_filters(scope),
        )
    )
    return int((await session.execute(stmt)).scalar_one())


def history_query(student_id: uuid.UUID, shared_only: bool) -> Select[Any]:
    """Application history rows (plan 6.5 ApplicationSummary)."""
    now: datetime = utcnow()
    next_interview = (
        select(func.min(Interview.scheduled_at))
        .where(
            Interview.application_id == Application.id,
            Interview.status.in_(UPCOMING_INTERVIEW_STATUSES),
            Interview.scheduled_at > now,
        )
        .correlate(Application)
        .scalar_subquery()
    )
    eval_filters = [Evaluation.application_id == Application.id, Evaluation.archived_at.is_(None)]
    if shared_only:
        eval_filters.append(Evaluation.shared_with_student.is_(True))
    eval_avg = select(func.avg(Evaluation.weighted_score)).where(*eval_filters).correlate(Application).scalar_subquery()
    return (
        select(
            Application,
            Internship,
            Company,
            Student,
            User,
            next_interview.label("next_interview_at"),
            eval_avg.label("evaluation_avg"),
        )
        .join(Internship, Internship.id == Application.internship_id)
        .join(Company, Company.id == Internship.company_id)
        .join(Student, Student.user_id == Application.student_id)
        .join(User, User.id == Student.user_id)
        .where(Application.student_id == student_id)
        .order_by(Application.created_at.desc(), Application.id)
    )
