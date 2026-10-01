"""Transactional side effects.

Everything here is *staged* on ``session.info`` while the request runs and dispatched by
``flush(session)`` only after the transaction committed (see ``db.managed_session``).

* ``notify``      - inserts a ``notifications`` row in the same transaction and stages a websocket publish
* ``audit``       - inserts an ``audit_logs`` row in the same transaction
* ``queue_email`` - stages Celery task ``emails.send``
* ``queue_task``  - stages any Celery task by string name

Tests replace ``side_effects.dispatcher`` with a collector (see tests/conftest.py).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import anyio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import utcnow
from app.core.request_context import get_request_context

log = logging.getLogger(__name__)

_KEY = "side_effects"


@dataclass
class _Publish:
    user_id: uuid.UUID
    payload: dict[str, Any]


@dataclass
class _Task:
    name: str
    kwargs: dict[str, Any] = field(default_factory=dict)
    countdown: int | None = None


class Dispatcher:
    """Real dispatcher: Redis pub/sub + Celery producer."""

    async def publish(self, user_id: uuid.UUID, message: dict[str, Any]) -> None:
        from app.core import redis as redis_core

        await redis_core.publish(f"user:{user_id}", message)

    async def send_task(self, name: str, kwargs: dict[str, Any], countdown: int | None = None) -> None:
        from app.core.celery_app import celery_app

        opts: dict[str, Any] = {}
        if countdown:
            opts["countdown"] = countdown
        await anyio.to_thread.run_sync(lambda: celery_app.send_task(name, kwargs=kwargs, **opts))

    async def unread_count(self, session: AsyncSession, user_id: uuid.UUID) -> int:
        from app.modules.notifications.models import Notification

        res = await session.execute(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id, Notification.read_at.is_(None)
            )
        )
        return int(res.scalar_one())


dispatcher: Dispatcher = Dispatcher()


def _staged(session: AsyncSession) -> list[Any]:
    return session.info.setdefault(_KEY, [])


def discard(session: AsyncSession) -> None:
    session.info.pop(_KEY, None)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat().replace("+00:00", "Z") if dt else None


def notify(
    session: AsyncSession,
    user_id: uuid.UUID,
    type: str,  # noqa: A002 - matches the column name
    title: str,
    body: str = "",
    link: str | None = None,
    data: dict[str, Any] | None = None,
):
    """Create a notification row for ``user_id`` and push it over the websocket after commit."""
    from app.modules.notifications.models import Notification

    n = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        type=type,
        title=title[:160],
        body=body,
        link=link,
        data=data or {},
        created_at=utcnow(),
    )
    session.add(n)
    payload = {
        "id": str(n.id),
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "link": n.link,
        "data": n.data,
        "read_at": None,
        "created_at": _iso(n.created_at),
    }
    _staged(session).append(_Publish(user_id, {"type": "notification", "data": payload}))
    return n


def queue_email(session: AsyncSession, template: str, to: str, context: dict[str, Any] | None = None) -> None:
    """Stage ``emails.send(template, to, context)``; context must be JSON-serialisable."""
    _staged(session).append(_Task("emails.send", {"template": template, "to": to, "context": context or {}}))


def queue_task(
    session: AsyncSession, name: str, kwargs: dict[str, Any] | None = None, countdown: int | None = None
) -> None:
    """Stage a Celery task by string name (kwargs must be JSON-serialisable)."""
    _staged(session).append(_Task(name, kwargs or {}, countdown))


def audit(
    session: AsyncSession,
    actor: Any,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
):
    """Add an audit_logs row. ``actor`` may be a User, a UUID or None. IP / UA come from the request context."""
    from app.modules.admin.models import AuditLog

    ctx = get_request_context()
    actor_id = getattr(actor, "id", actor)
    if isinstance(entity_id, str):
        entity_id = uuid.UUID(entity_id)
    row = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        ip=ctx.ip,
        user_agent=(ctx.user_agent or None) and ctx.user_agent[:500],
    )
    session.add(row)
    return row


async def flush(session: AsyncSession) -> None:
    """Dispatch staged side effects. Never raises: failures are logged (the DB state is already committed)."""
    events: list[Any] = session.info.pop(_KEY, [])
    unread_for: dict[uuid.UUID, int] = {}
    for ev in events:
        try:
            if isinstance(ev, _Publish):
                await dispatcher.publish(ev.user_id, ev.payload)
                if ev.user_id not in unread_for:
                    unread_for[ev.user_id] = await dispatcher.unread_count(session, ev.user_id)
                    await dispatcher.publish(
                        ev.user_id, {"type": "unread_count", "data": {"count": unread_for[ev.user_id]}}
                    )
            elif isinstance(ev, _Task):
                await dispatcher.send_task(ev.name, ev.kwargs, ev.countdown)
        except Exception:  # noqa: BLE001
            log.exception("side effect failed: %r", ev)
