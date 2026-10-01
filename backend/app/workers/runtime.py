"""Async plumbing for Celery tasks (plan 1.3).

Tasks are plain sync functions; each one calls ``run_async(coro)`` which runs the coroutine in a *fresh*
event loop (``asyncio.run``). Inside, ``worker_session()`` builds its own ``NullPool`` engine, so nothing is
shared with the API's engine/loop (asyncpg connections and the cached Redis client are loop-bound).
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core import side_effects
from app.core.base import utcnow
from app.core.config import settings

log = logging.getLogger(__name__)


def run_async[T](coro: Awaitable[T]) -> T:
    """Run ``coro`` to completion in a new event loop and release loop-bound resources afterwards."""

    async def _runner() -> T:
        try:
            return await coro
        finally:
            # core.redis keeps a module-level client bound to the loop it was created in
            from app.core import redis as redis_core

            await redis_core.close_redis()

    return asyncio.run(_runner())


@asynccontextmanager
async def worker_session() -> AsyncIterator[AsyncSession]:
    """A session on a private NullPool engine. Commits on success, rolls back on error, then flushes the
    staged side effects (``notify`` publishes, ``queue_email`` / ``queue_task``) exactly like ``get_db``."""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except BaseException:
                await session.rollback()
                side_effects.discard(session)
                raise
            await side_effects.flush(session)
    finally:
        await engine.dispose()


async def publish_user_event(user_id: uuid.UUID | str, message: dict[str, Any]) -> None:
    """Publish ``message`` on ``user:{id}`` (the websocket fan-out channel). Never raises."""
    client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await client.publish(f"user:{user_id}", json.dumps(message, default=str))
    except Exception:  # noqa: BLE001
        log.exception("could not publish event for user %s", user_id)
    finally:
        await client.aclose()


def iso_z(dt: Any) -> str | None:
    return dt.isoformat().replace("+00:00", "Z") if dt else None


async def mark_job_failed(job_id: uuid.UUID | str, error: str) -> None:
    """Last-resort failure handler used by the thin task wrappers: FAILED + ``job`` event for the requester."""
    from app.modules.admin.models import Job

    jid = job_id if isinstance(job_id, uuid.UUID) else uuid.UUID(str(job_id))
    async with worker_session() as session:
        job = await session.get(Job, jid)
        if job is None or job.status in ("SUCCEEDED", "FAILED"):
            return
        job.status = "FAILED"
        job.error = error[:2000]
        job.finished_at = utcnow()
        await session.flush()
        requester = job.requested_by
        payload = {
            "id": str(job.id),
            "type": job.type,
            "status": job.status,
            "progress": job.progress,
            "params": job.params,
            "result": job.result,
            "error": job.error,
            "download_url": None,
            "created_at": iso_z(job.created_at),
            "finished_at": iso_z(job.finished_at),
        }
    if requester:
        await publish_user_event(requester, {"type": "job", "data": payload})


async def call_job_function(fn: Callable[..., Awaitable[Any]], job_id: str) -> Any:
    """Call a sibling-owned ``async def run_*_job(job_id)``: passes ``uuid.UUID`` unless the parameter is
    annotated ``str``. On any exception the job is marked FAILED (if the callee did not) and the error re-raised."""
    params = list(inspect.signature(fn).parameters.values())
    wants_str = bool(params) and params[0].annotation in (str, "str")
    arg: Any = job_id if wants_str else uuid.UUID(str(job_id))
    try:
        return await fn(arg)
    except Exception as exc:
        log.exception("job %s failed in %s", job_id, getattr(fn, "__qualname__", fn))
        await mark_job_failed(job_id, f"{type(exc).__name__}: {exc}")
        raise
