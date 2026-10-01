"""Notification centre: every operation is scoped to the caller (someone else's id is a 404)."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import side_effects
from app.core.base import utcnow
from app.core.errors import not_found
from app.core.pagination import PageParams, make_page, paginate
from app.modules.notifications import repository as repo
from app.modules.notifications.models import Notification
from app.modules.notifications.schemas import NotificationOut


async def list_notifications(
    session: AsyncSession, user_id: uuid.UUID, params: PageParams, unread_only: bool = False
) -> dict[str, Any]:
    rows, total = await paginate(session, repo.list_query(user_id, unread_only), params)
    return make_page([NotificationOut.model_validate(r) for r in rows], total, params)


async def unread_count(session: AsyncSession, user_id: uuid.UUID) -> int:
    return await repo.unread_count(session, user_id)


def _stage_unread_push(session: AsyncSession, user_id: uuid.UUID, count: int) -> None:
    """Keep other open tabs / the bell in sync: publish the new unread count after commit."""
    side_effects._staged(session).append(  # noqa: SLF001 - same package family, no public hook for bare counts
        side_effects._Publish(user_id, {"type": "unread_count", "data": {"count": count}})  # noqa: SLF001
    )


async def mark_read(session: AsyncSession, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
    n = await repo.get_owned(session, user_id, notification_id)
    if n is None:
        raise not_found("Notification not found")
    if n.read_at is None:
        n.read_at = utcnow()
        await session.flush()
        _stage_unread_push(session, user_id, await repo.unread_count(session, user_id))
    return n


async def mark_all_read(session: AsyncSession, user_id: uuid.UUID) -> int:
    changed = await repo.mark_all_read(session, user_id, utcnow())
    if changed:
        _stage_unread_push(session, user_id, 0)
    return changed


async def delete(session: AsyncSession, user_id: uuid.UUID, notification_id: uuid.UUID) -> None:
    if not await repo.delete_owned(session, user_id, notification_id):
        raise not_found("Notification not found")
    _stage_unread_push(session, user_id, await repo.unread_count(session, user_id))
