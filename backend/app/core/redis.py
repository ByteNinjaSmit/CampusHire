"""Shared async Redis client, JSON cache helpers, fixed-window rate limiter and pub/sub publish."""

import json
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings

_client: Redis | None = None


def get_redis() -> Redis:
    global _client
    if _client is None:
        _client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def cache_get(key: str) -> Any | None:
    raw = await get_redis().get(key)
    return None if raw is None else json.loads(raw)


async def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    await get_redis().set(key, json.dumps(value, default=str), ex=ttl)


async def cache_delete(*keys: str) -> None:
    if keys:
        await get_redis().delete(*keys)


async def rate_limit_hit(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Fixed window counter. Returns (allowed, retry_after_seconds)."""
    r = get_redis()
    rkey = f"rl:{key}"
    count = await r.incr(rkey)
    if count == 1:
        await r.expire(rkey, window_seconds)
    if count > limit:
        ttl = await r.ttl(rkey)
        if ttl is None or ttl < 0:
            await r.expire(rkey, window_seconds)
            ttl = window_seconds
        return False, int(ttl)
    return True, 0


async def publish(channel: str, message: dict[str, Any]) -> None:
    await get_redis().publish(channel, json.dumps(message, default=str))
