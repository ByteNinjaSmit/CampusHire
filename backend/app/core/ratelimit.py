"""Rate limiting (plan 4.3): helper + dependency factory. Disabled when RATE_LIMIT_ENABLED=false."""

from collections.abc import Awaitable, Callable

from fastapi import Request

from app.core import redis as redis_core
from app.core.config import settings
from app.core.errors import rate_limited
from app.core.security import try_decode_subject


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


async def check_rate_limit(key: str, limit: int, window_seconds: int) -> None:
    """Raise 429 RATE_LIMITED (with Retry-After) when ``key`` exceeded ``limit`` hits in the window."""
    if not settings.RATE_LIMIT_ENABLED:
        return
    allowed, retry_after = await redis_core.rate_limit_hit(key, limit, window_seconds)
    if not allowed:
        raise rate_limited(retry_after)


def identity_of(request: Request) -> str:
    """``user:<sub>`` when a valid bearer token is present, else ``ip:<addr>``."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        sub = try_decode_subject(auth[7:].strip())
        if sub:
            return f"user:{sub}"
    return f"ip:{client_ip(request)}"


def rate_limit(name: str, limit: int, window_seconds: int, by: str = "identity") -> Callable[[Request], Awaitable[None]]:
    """Dependency factory. ``by`` is ``"ip"`` or ``"identity"`` (user when authenticated, else ip)."""

    async def _dep(request: Request) -> None:
        who = f"ip:{client_ip(request)}" if by == "ip" else identity_of(request)
        await check_rate_limit(f"{name}:{who}", limit, window_seconds)

    return _dep


# Global default: 300/min per user or ip (applied on the /api/v1 router)
global_rate_limit = rate_limit("global", 300, 60)
register_rate_limit = rate_limit("register", 10, 3600, by="ip")
