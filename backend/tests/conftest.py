"""Test infrastructure (plan 9.1).

* Env is configured BEFORE the app is imported: DATABASE_URL -> test DB, REDIS_URL -> redis db 15.
* Session fixture drops/recreates the schema in the test DB and runs ``alembic upgrade head``.
* Each test runs inside a connection-level transaction with SAVEPOINT semantics and is rolled back afterwards.
  (The race test in test_application_race.py uses real, separate sessions and truncates afterwards.)
* ``fake_storage`` replaces MinIO, ``captured`` replaces Redis pub/sub + Celery dispatch,
  Redis is real (db 15, flushed per test). Rate limiting is off unless a test turns it on.

Run locally:
    $env:TEST_DATABASE_URL="postgresql+asyncpg://campushire:campushire@localhost:5433/campushire_test"
    $env:REDIS_URL="redis://localhost:6379/0"   # db number is replaced by 15 automatically
    python -m pytest
"""

import asyncio
import os
import re
import sys
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://campushire:campushire@localhost:5433/campushire_test"
)


def _with_redis_db(url: str, db: int) -> str:
    return re.sub(r"/\d+$", f"/{db}", url) if re.search(r"/\d+$", url) else url.rstrip("/") + f"/{db}"


TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL") or _with_redis_db(
    os.environ.get("REDIS_URL", "redis://localhost:6379/0"), 15
)

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["TEST_DATABASE_URL"] = TEST_DATABASE_URL
os.environ["REDIS_URL"] = TEST_REDIS_URL
os.environ["CELERY_BROKER_URL"] = _with_redis_db(TEST_REDIS_URL, 14)
os.environ["CELERY_RESULT_BACKEND"] = _with_redis_db(TEST_REDIS_URL, 14)
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["COOKIE_SECURE"] = "false"
os.environ["ENVIRONMENT"] = "test"

import asyncpg  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.core import redis as redis_core  # noqa: E402
from app.core import side_effects  # noqa: E402
from app.core.db import get_db, managed_session  # noqa: E402
from app.core.storage import get_storage  # noqa: E402
from app.main import app  # noqa: E402


# ---------------------------------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------------------------------
class FakeStorage:
    """In-memory replacement for app.core.storage.Storage (same async interface).

    ``put(key, data)`` simulates the browser having uploaded the object; objects are looked up by key.
    """

    def __init__(self) -> None:
        self.objects: dict[str, dict[str, Any]] = {}
        self.deleted: list[str] = []

    # test helpers
    def put(self, key: str, data: bytes, content_type: str = "application/pdf", bucket: str | None = None) -> None:
        self.objects[key] = {"data": data, "content_type": content_type, "bucket": bucket}

    def has(self, key: str) -> bool:
        return key in self.objects

    # Storage interface
    async def presign_post(
        self, bucket: str, key: str, content_type: str, max_bytes: int = 5_242_880, expires: int = 600
    ) -> dict[str, Any]:
        return {
            "url": f"http://fake-storage.local/{bucket}",
            "fields": {"key": key, "Content-Type": content_type, "policy": "fake", "x-amz-signature": "fake"},
        }

    async def presign_get(self, bucket: str, key: str, filename: str | None = None, expires: int = 300) -> str:
        return f"http://fake-storage.local/{bucket}/{key}?sig=fake&expires={expires}"

    async def head(self, bucket: str, key: str) -> dict[str, Any] | None:
        obj = self.objects.get(key)
        if obj is None:
            return None
        return {"size": len(obj["data"]), "content_type": obj["content_type"]}

    async def read_range(self, bucket: str, key: str, start: int = 0, end: int = 4) -> bytes:
        return self.objects[key]["data"][start : end + 1]

    async def get_object(self, bucket: str, key: str) -> bytes:
        return self.objects[key]["data"]

    async def delete(self, bucket: str, key: str) -> None:
        self.objects.pop(key, None)
        self.deleted.append(key)

    async def put_object(
        self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        self.put(key, data, content_type, bucket)


class Captured(side_effects.Dispatcher):
    """Collects staged side effects instead of publishing to Redis / calling Celery."""

    def __init__(self) -> None:
        self.messages: list[tuple[uuid.UUID, dict[str, Any]]] = []
        self.notifications: list[dict[str, Any]] = []  # websocket "notification" payloads
        self.emails: list[dict[str, Any]] = []  # kwargs of emails.send: template / to / context
        self.tasks: list[tuple[str, dict[str, Any]]] = []  # every other Celery task: (name, kwargs)

    async def publish(self, user_id: uuid.UUID, message: dict[str, Any]) -> None:
        self.messages.append((user_id, message))
        if message.get("type") == "notification":
            self.notifications.append({"user_id": user_id, **message["data"]})

    async def send_task(self, name: str, kwargs: dict[str, Any], countdown: int | None = None) -> None:
        if name == "emails.send":
            self.emails.append(kwargs)
        else:
            self.tasks.append((name, kwargs))

    def emails_to(self, address: str, template: str | None = None) -> list[dict[str, Any]]:
        return [e for e in self.emails if e["to"] == address and (template is None or e["template"] == template)]


# ---------------------------------------------------------------------------------------------------
# DB bootstrap (session scoped)
# ---------------------------------------------------------------------------------------------------
async def _ensure_database() -> None:
    dsn = TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    db_name = dsn.rsplit("/", 1)[-1]
    try:
        conn = await asyncpg.connect(dsn)
        await conn.close()
        return
    except asyncpg.InvalidCatalogNameError:
        pass
    admin_dsn = dsn.rsplit("/", 1)[0] + "/postgres"
    conn = await asyncpg.connect(admin_dsn)
    try:
        await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()


def _alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return cfg


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def _database() -> AsyncIterator[None]:
    await _ensure_database()
    admin_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await admin_engine.dispose()
    # alembic's env.py uses asyncio.run(), so run it in a worker thread (we are inside a running loop)
    await asyncio.to_thread(command.upgrade, _alembic_config(), "head")
    yield
    await redis_core.close_redis()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _flush_redis() -> AsyncIterator[None]:
    await redis_core.get_redis().flushdb()
    yield


@pytest_asyncio.fixture
async def db_conn(engine) -> AsyncIterator[AsyncConnection]:
    """One connection per test whose outer transaction is rolled back at the end."""
    async with engine.connect() as conn:
        outer = await conn.begin()
        try:
            yield conn
        finally:
            await outer.rollback()


@pytest_asyncio.fixture
async def db(db_conn: AsyncConnection) -> AsyncIterator[AsyncSession]:
    """The test's own session (use it with the factories). It runs inside a SAVEPOINT of ``db_conn``.

    API requests get a *separate* session on the same connection (see ``client``), exactly like production
    (one session per request), so data created through ``db`` + ``flush`` is visible to requests, and a failing
    request only rolls back its own work. Objects the test already holds are NOT refreshed automatically after a
    request modified them: call ``await db.refresh(obj)`` (or select the columns again) before asserting.
    """
    session = AsyncSession(bind=db_conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture
def fake_storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def captured() -> Captured:
    return Captured()


@pytest_asyncio.fixture
async def client(
    db: AsyncSession, db_conn: AsyncConnection, fake_storage: FakeStorage, captured: Captured
) -> AsyncIterator[AsyncClient]:
    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        await db.flush()  # make factory-created rows visible to the request session (same connection)
        async with AsyncSession(
            bind=db_conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        ) as request_session:
            async with managed_session(request_session):
                yield request_session

    previous_dispatcher = side_effects.dispatcher
    side_effects.dispatcher = captured
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_storage] = lambda: fake_storage
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        side_effects.dispatcher = previous_dispatcher


@pytest.fixture
def enable_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
