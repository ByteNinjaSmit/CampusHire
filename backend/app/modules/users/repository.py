import uuid
from typing import Any

from sqlalchemy import Select, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RefreshToken
from app.modules.companies.models import Company, CompanyMember
from app.modules.documents.models import Document
from app.modules.faculty.models import Faculty
from app.modules.students.models import Student
from app.modules.users.models import User


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    return (await session.execute(select(User).where(User.email == email.lower()))).scalar_one_or_none()


async def get_student(session: AsyncSession, user_id: uuid.UUID) -> Student | None:
    return (await session.execute(select(Student).where(Student.user_id == user_id))).scalar_one_or_none()


async def get_faculty(session: AsyncSession, user_id: uuid.UUID) -> Faculty | None:
    return (await session.execute(select(Faculty).where(Faculty.user_id == user_id))).scalar_one_or_none()


async def get_company_membership(session: AsyncSession, user_id: uuid.UUID) -> tuple[CompanyMember, Company] | None:
    row = (
        await session.execute(
            select(CompanyMember, Company)
            .join(Company, Company.id == CompanyMember.company_id)
            .where(CompanyMember.user_id == user_id)
        )
    ).first()
    return (row[0], row[1]) if row else None


async def get_document(session: AsyncSession, document_id: uuid.UUID) -> Document | None:
    return (await session.execute(select(Document).where(Document.id == document_id))).scalar_one_or_none()


async def get_company(session: AsyncSession, company_id: uuid.UUID) -> Company | None:
    return (await session.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()


def list_query(role: str | None, q: str | None, is_active: bool | None) -> Select[Any]:
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.full_name.ilike(like), User.email.ilike(like)))
    return stmt.order_by(User.created_at.desc(), User.id)


async def revoke_all_refresh_tokens(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=func.now())
    )


async def active_admin_ids(session: AsyncSession) -> list[uuid.UUID]:
    rows = await session.execute(select(User.id).where(User.role == "ADMIN", User.is_active.is_(True)))
    return list(rows.scalars().all())
