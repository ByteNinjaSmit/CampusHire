import uuid
from datetime import datetime

from sqlalchemy import Select, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification


def list_query(user_id: uuid.UUID, unread_only: bool = False) -> Select[tuple[Notification]]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    return stmt.order_by(Notification.created_at.desc(), Notification.id.desc())


async def get_owned(session: AsyncSession, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification | None:
    res = await session.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
    )
    return res.scalar_one_or_none()


async def unread_count(session: AsyncSession, user_id: uuid.UUID) -> int:
    res = await session.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
    )
    return int(res.scalar_one())


async def mark_all_read(session: AsyncSession, user_id: uuid.UUID, now: datetime) -> int:
    res = await session.execute(
        update(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None)).values(read_at=now)
    )
    return int(res.rowcount or 0)  # type: ignore[attr-defined]  # CursorResult from a DML statement


async def delete_owned(session: AsyncSession, user_id: uuid.UUID, notification_id: uuid.UUID) -> bool:
    res = await session.execute(
        delete(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
    )
    return bool(res.rowcount)  # type: ignore[attr-defined]
