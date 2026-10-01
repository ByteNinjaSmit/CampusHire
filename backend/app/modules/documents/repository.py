import uuid
from typing import Any

from sqlalchemy import Select, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.applications.models import Application
from app.modules.documents.models import Document
from app.modules.users.models import User


def in_use_clause() -> Any:
    """True when a non-withdrawn application references the document as its resume."""
    return exists().where(Application.resume_document_id == Document.id, Application.status != "WITHDRAWN")


def rows_query() -> Select[Any]:
    """(Document, owner_full_name, in_use) for non-deleted documents."""
    return (
        select(Document, User.full_name, in_use_clause().label("in_use"))
        .join(User, User.id == Document.owner_id)
        .where(Document.deleted_at.is_(None))
    )


async def get_row(session: AsyncSession, document_id: uuid.UUID) -> tuple[Document, str, bool] | None:
    row = (await session.execute(rows_query().where(Document.id == document_id))).first()
    return (row[0], row[1], bool(row[2])) if row else None


async def get(session: AsyncSession, document_id: uuid.UUID) -> Document | None:
    return (
        await session.execute(select(Document).where(Document.id == document_id, Document.deleted_at.is_(None)))
    ).scalar_one_or_none()


async def targets_owned_internship(session: AsyncSession, document_id: uuid.UUID, owned_ids: Select[Any]) -> bool:
    """True if an application using the document targets one of the internships in ``owned_ids``."""
    stmt = (
        select(Application.id)
        .where(Application.resume_document_id == document_id, Application.internship_id.in_(owned_ids))
        .limit(1)
    )
    return (await session.execute(stmt)).first() is not None


async def is_referenced(session: AsyncSession, document_id: uuid.UUID) -> bool:
    return (
        await session.execute(select(Application.id).where(Application.resume_document_id == document_id).limit(1))
    ).first() is not None
