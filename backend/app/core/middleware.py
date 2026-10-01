"""Pure-ASGI middleware: request id, security headers, request context and per-minute metrics in Redis."""

import logging
import time
import uuid
from datetime import UTC, datetime

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core import redis as redis_core
from app.core.request_context import RequestContext, reset_request_context, set_request_context

log = logging.getLogger(__name__)

LATENCY_BUCKETS_MS = (5, 10, 25, 50, 100, 250, 500, 1000, 2500)
METRICS_TTL_SECONDS = 2 * 3600
SKIP_METRICS_PREFIXES = ("/healthz", "/readyz", "/docs", "/redoc", "/api/v1/openapi.json")

SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
}


def metrics_key(dt: datetime) -> str:
    return f"metrics:{dt.strftime('%Y%m%d%H%M')}"


def latency_bucket(ms: float) -> str:
    for b in LATENCY_BUCKETS_MS:
        if ms <= b:
            return f"lat_le_{b}"
    return "lat_le_inf"


async def record_metrics(status: int, elapsed_ms: float) -> None:
    """HINCRBY count / errors / latency histogram bucket / latency sum on ``metrics:{yyyyMMddHHmm}`` (TTL 2h)."""
    try:
        key = metrics_key(datetime.now(UTC))
        r = redis_core.get_redis()
        pipe = r.pipeline(transaction=False)
        pipe.hincrby(key, "count", 1)
        if status >= 500:
            pipe.hincrby(key, "errors", 1)
        pipe.hincrby(key, latency_bucket(elapsed_ms), 1)
        pipe.hincrbyfloat(key, "lat_sum_ms", round(elapsed_ms, 2))
        pipe.expire(key, METRICS_TTL_SECONDS)
        await pipe.execute()
    except Exception:  # noqa: BLE001 - metrics must never break a request
        log.debug("metrics write failed", exc_info=True)


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = headers.get("x-request-id") or uuid.uuid4().hex
        client = scope.get("client")
        ctx = RequestContext(
            request_id=request_id,
            ip=client[0] if client else None,
            user_agent=headers.get("user-agent"),
        )
        scope.setdefault("state", {})["request_id"] = request_id
        token = set_request_context(ctx)
        started = time.perf_counter()
        status_holder = {"status": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                raw = message.setdefault("headers", [])
                raw.append((b"x-request-id", request_id.encode()))
                for k, v in SECURITY_HEADERS.items():
                    raw.append((k.encode(), v.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            reset_request_context(token)
            path = scope.get("path", "")
            if not path.startswith(SKIP_METRICS_PREFIXES):
                await record_metrics(status_holder["status"], (time.perf_counter() - started) * 1000)
