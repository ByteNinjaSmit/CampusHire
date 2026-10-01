"""System health (plan 4.4 / WP4): db, redis, minio (per bucket + total size), celery workers, broker queue depth.

Every probe is bounded by a timeout and never raises; a failure is reported as ``status="down"``.
"""

import logging
import time
from datetime import UTC, datetime
from typing import Any

import anyio
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import redis as redis_core
from app.core.config import settings
from app.modules.admin import schemas as s

log = logging.getLogger(__name__)

PROBE_TIMEOUT = 3.0
MINIO_TIMEOUT = 6.0
MAX_LIST_PAGES = 20  # 20 * 1000 objects per bucket; beyond that the size is reported as truncated
CELERY_QUEUE = "celery"


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


def _down(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"[:300]


async def check_db(session: AsyncSession) -> s.ComponentHealth:
    started = time.perf_counter()
    try:
        with anyio.fail_after(PROBE_TIMEOUT):
            await session.execute(text("SELECT 1"))
        return s.ComponentHealth(status="ok", latency_ms=_ms(started))
    except Exception as exc:  # noqa: BLE001
        return s.ComponentHealth(status="down", latency_ms=_ms(started), detail=_down(exc))


async def check_redis() -> s.ComponentHealth:
    started = time.perf_counter()
    try:
        with anyio.fail_after(PROBE_TIMEOUT):
            await redis_core.get_redis().ping()
        return s.ComponentHealth(status="ok", latency_ms=_ms(started))
    except Exception as exc:  # noqa: BLE001
        return s.ComponentHealth(status="down", latency_ms=_ms(started), detail=_down(exc))


def _probe_bucket(bucket: str) -> s.BucketHealth:
    from app.core.storage import s3_internal

    client = s3_internal()
    started = time.perf_counter()
    try:
        client.head_bucket(Bucket=bucket)
    except Exception as exc:  # noqa: BLE001
        return s.BucketHealth(bucket=bucket, status="down", latency_ms=_ms(started), detail=_down(exc))
    latency = _ms(started)
    total = 0
    count = 0
    truncated = False
    token: str | None = None
    try:
        for page in range(MAX_LIST_PAGES):
            kwargs: dict[str, Any] = {"Bucket": bucket}
            if token:
                kwargs["ContinuationToken"] = token
            resp = client.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []):
                total += int(obj["Size"])
                count += 1
            if not resp.get("IsTruncated"):
                break
            token = resp.get("NextContinuationToken")
            if page == MAX_LIST_PAGES - 1:
                truncated = True
    except Exception as exc:  # noqa: BLE001
        return s.BucketHealth(bucket=bucket, status="ok", latency_ms=latency, detail=f"size unavailable: {_down(exc)}")
    return s.BucketHealth(
        bucket=bucket, status="ok", latency_ms=latency, object_count=count, size_bytes=total, truncated=truncated
    )


async def check_minio() -> s.MinioHealth:
    started = time.perf_counter()
    buckets: list[s.BucketHealth] = []
    try:
        for name in settings.buckets:
            try:
                with anyio.fail_after(MINIO_TIMEOUT):
                    buckets.append(await anyio.to_thread.run_sync(_probe_bucket, name, abandon_on_cancel=True))
            except TimeoutError:
                buckets.append(s.BucketHealth(bucket=name, status="down", detail="timeout"))
    except Exception as exc:  # noqa: BLE001
        return s.MinioHealth(status="down", latency_ms=_ms(started), detail=_down(exc), buckets=buckets)
    ok = bool(buckets) and all(b.status == "ok" for b in buckets)
    return s.MinioHealth(
        status="ok" if ok else "down",
        latency_ms=_ms(started),
        detail=None if ok else "one or more buckets unavailable",
        buckets=buckets,
        total_size_bytes=sum(b.size_bytes or 0 for b in buckets),
    )


def _celery_ping() -> dict[str, Any] | None:
    from app.core.celery_app import celery_app

    return celery_app.control.inspect(timeout=1).ping()


async def check_celery() -> s.CeleryHealth:
    started = time.perf_counter()
    try:
        with anyio.fail_after(PROBE_TIMEOUT + 2):
            replies = await anyio.to_thread.run_sync(_celery_ping, abandon_on_cancel=True)
    except Exception as exc:  # noqa: BLE001
        return s.CeleryHealth(status="down", latency_ms=_ms(started), detail=_down(exc))
    if not replies:
        return s.CeleryHealth(status="down", latency_ms=_ms(started), detail="no workers responded")
    return s.CeleryHealth(status="ok", latency_ms=_ms(started), workers=sorted(replies))


async def queue_depth() -> int | None:
    """``LLEN celery`` on the broker database (the default Celery queue)."""
    client: Redis | None = None
    try:
        client = Redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
        with anyio.fail_after(PROBE_TIMEOUT):
            return int(await client.llen(CELERY_QUEUE))
    except Exception:  # noqa: BLE001
        log.debug("queue depth unavailable", exc_info=True)
        return None
    finally:
        if client is not None:
            await client.aclose()


def overall_status(
    db: s.ComponentHealth, redis: s.ComponentHealth, minio: s.ComponentHealth, celery: s.ComponentHealth
) -> str:
    if db.status != "ok" or redis.status != "ok":
        return "down"
    if minio.status != "ok" or celery.status != "ok":
        return "degraded"
    return "ok"


async def collect_health(session: AsyncSession) -> s.HealthResponse:
    db = await check_db(session)
    redis = await check_redis()
    minio = await check_minio()
    celery = await check_celery()
    depth = await queue_depth()
    return s.HealthResponse(
        status=overall_status(db, redis, minio, celery),  # type: ignore[arg-type]  # literal str from helper
        checked_at=datetime.now(UTC),
        db=db,
        redis=redis,
        minio=minio,
        celery=celery,
        queue_depth=depth,
    )
