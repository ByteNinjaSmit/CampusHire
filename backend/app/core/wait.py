"""Wait for Postgres, Redis and MinIO (max 60 s). Used by docker/entrypoint.sh: ``python -m app.core.wait``."""

import asyncio
import socket
import sys
import time
import urllib.request
from urllib.parse import urlparse

import asyncpg

from app.core.config import settings

TIMEOUT_SECONDS = 60


def _tcp(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


async def _db_ok() -> bool:
    dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    try:
        conn = await asyncpg.connect(dsn, timeout=3)
        await conn.close()
        return True
    except Exception:  # noqa: BLE001
        return False


def _redis_ok() -> bool:
    u = urlparse(settings.REDIS_URL)
    return _tcp(u.hostname or "localhost", u.port or 6379)


def _minio_ok() -> bool:
    url = settings.MINIO_ENDPOINT.rstrip("/") + "/minio/health/live"
    try:
        with urllib.request.urlopen(url, timeout=3) as r:  # noqa: S310 - fixed internal URL
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def main() -> int:
    deadline = time.monotonic() + TIMEOUT_SECONDS
    pending = {"postgres", "redis", "minio"}
    while pending and time.monotonic() < deadline:
        if "postgres" in pending and asyncio.run(_db_ok()):
            pending.discard("postgres")
            print("wait: postgres ready", flush=True)
        if "redis" in pending and _redis_ok():
            pending.discard("redis")
            print("wait: redis ready", flush=True)
        if "minio" in pending and _minio_ok():
            pending.discard("minio")
            print("wait: minio ready", flush=True)
        if pending:
            time.sleep(1)
    if pending:
        print(f"wait: timed out waiting for {sorted(pending)}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
