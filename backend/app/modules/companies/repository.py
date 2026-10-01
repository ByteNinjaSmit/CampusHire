import uuid
from typing import Any

from sqlalchemy import Select, and_, exists, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import utcnow
from app.modules.applications.models import Application
from app.modules.companies.models import Company, CompanyMember
from app.modules.documents.models import Document
from app.modules.feedback.models import StudentFeedback
from app.modules.internships.models import Internship, SavedInternship
from app.modules.students.models import Student
from app.modules.users.models import User

DIMENSIONS = ("company_culture", "mentorship", "technical_learning", "work_environment")


async def get(session: AsyncSession, company_id: uuid.UUID) -> Company | None:
    return (await session.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()


def visibility_clause(user: User, member_company_id: uuid.UUID | None) -> Any:
    """Companies a non-admin may see: ACTIVE and not archived, plus ones they created / belong to."""
    if user.role == "ADMIN":
        return True
    clauses = [and_(Company.status == "ACTIVE", Company.archived_at.is_(None))]
    if user.role == "FACULTY":
        clauses.append(Company.created_by == user.id)
    if user.role == "COMPANY" and member_company_id is not None:
        clauses.append(Company.id == member_company_id)
    return or_(*clauses)


def list_query(
    user: User,
    member_company_id: uuid.UUID | None,
    q: str | None,
    location: str | None,
    industry: str | None,
    status: str | None,
) -> Select[Any]:
    stmt = select(Company)
    if user.role != "ADMIN":
        stmt = stmt.where(visibility_clause(user, member_company_id))
    if q:
        escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Company.name.ilike(f"%{escaped}%", escape="\\"))
    if location:
        escaped = location.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Company.location.ilike(f"%{escaped}%", escape="\\"))
    if industry:
        stmt = stmt.where(Company.industry == industry)
    if status:
        stmt = stmt.where(Company.status == status)
    return stmt.order_by(Company.name, Company.id)


async def rating_summaries(session: AsyncSession, company_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, Any]]:
    if not company_ids:
        return {}
    cols = [func.avg(getattr(StudentFeedback, d)) for d in DIMENSIONS]
    rows = await session.execute(
        select(StudentFeedback.company_id, func.count(), func.avg(StudentFeedback.overall), *cols)
        .where(StudentFeedback.company_id.in_(company_ids))
        .group_by(StudentFeedback.company_id)
    )
    out: dict[uuid.UUID, dict[str, Any]] = {}
    for cid, count, overall, *dims in rows.all():
        out[cid] = {
            "count": int(count),
            "overall": _r(overall),
            **{d: _r(v) for d, v in zip(DIMENSIONS, dims, strict=True)},
            "distribution": {str(i): 0 for i in range(1, 6)},
        }
    dist = await session.execute(
        select(StudentFeedback.company_id, StudentFeedback.overall, func.count())
        .where(StudentFeedback.company_id.in_(company_ids))
        .group_by(StudentFeedback.company_id, StudentFeedback.overall)
    )
    for cid, rating, n in dist.all():
        if cid in out:
            out[cid]["distribution"][str(int(rating))] = int(n)
    return out


def _r(v: Any) -> float | None:
    return None if v is None else round(float(v), 2)


def open_internship_clause() -> Any:
    return and_(
        Internship.status == "APPROVED", Internship.archived_at.is_(None), Internship.application_deadline > utcnow()
    )


async def open_counts(session: AsyncSession, company_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not company_ids:
        return {}
    rows = await session.execute(
        select(Internship.company_id, func.count())
        .where(Internship.company_id.in_(company_ids), open_internship_clause())
        .group_by(Internship.company_id)
    )
    return {cid: int(n) for cid, n in rows.all()}


async def internship_count(session: AsyncSession, company_id: uuid.UUID) -> int:
    return int(
        (await session.execute(select(func.count()).select_from(Internship).where(Internship.company_id == company_id)))
        .scalar_one()
    )


async def logo_documents(session: AsyncSession, document_ids: list[uuid.UUID]) -> dict[uuid.UUID, Document]:
    if not document_ids:
        return {}
    rows = await session.execute(
        select(Document).where(
            Document.id.in_(document_ids), Document.deleted_at.is_(None), Document.status == "UPLOADED"
        )
    )
    return {d.id: d for d in rows.scalars().all()}


async def members(session: AsyncSession, company_id: uuid.UUID) -> list[tuple[CompanyMember, User]]:
    rows = await session.execute(
        select(CompanyMember, User)
        .join(User, User.id == CompanyMember.user_id)
        .where(CompanyMember.company_id == company_id)
        .order_by(User.full_name, User.id)
    )
    return [(r[0], r[1]) for r in rows.all()]


async def member_user_ids(session: AsyncSession, company_id: uuid.UUID) -> list[uuid.UUID]:
    rows = await session.execute(select(CompanyMember.user_id).where(CompanyMember.company_id == company_id))
    return list(rows.scalars().all())


async def recent_feedback(session: AsyncSession, company_id: uuid.UUID, limit: int = 10) -> list[Any]:
    rows = await session.execute(
        select(StudentFeedback, User.full_name, Internship.title)
        .join(Student, Student.user_id == StudentFeedback.student_id)
        .join(User, User.id == Student.user_id)
        .join(Internship, Internship.id == StudentFeedback.internship_id)
        .where(StudentFeedback.company_id == company_id)
        .order_by(StudentFeedback.created_at.desc(), StudentFeedback.id)
        .limit(limit)
    )
    return list(rows.all())


def internships_query(user: User, member_company_id: uuid.UUID | None, company_id: uuid.UUID) -> Select[Any]:
    """(Internship, is_saved, application_count) for one company, scoped to what the viewer may see."""
    from app.core.permissions import owned_internships_clause

    app_count = (
        select(func.count()).select_from(Application).where(Application.internship_id == Internship.id)
        .correlate(Internship).scalar_subquery()
    )
    if user.role == "STUDENT":
        saved: Any = exists().where(
            SavedInternship.internship_id == Internship.id, SavedInternship.student_id == user.id
        )
    else:
        saved = literal(False)
    stmt = select(Internship, saved.label("is_saved"), app_count.label("application_count")).where(
        Internship.company_id == company_id
    )
    if user.role == "STUDENT":
        stmt = stmt.where(open_internship_clause())
    elif user.role != "ADMIN":
        stmt = stmt.where(or_(open_internship_clause(), owned_internships_clause(user, member_company_id)))
    return stmt.order_by(Internship.created_at.desc(), Internship.id)
