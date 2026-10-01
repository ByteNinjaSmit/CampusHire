"""NTF: notification REST endpoints, unread push and the realtime websocket (plan 4.4 / 6.10)."""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import redis as redis_core
from app.core import side_effects
from app.core.security import create_access_token
from app.modules.notifications import ws
from app.modules.notifications.models import Notification
from tests.factories import auth_headers, make_student, make_user



async def _make_notification(db: AsyncSession, user_id, title="Hello", read=False, age_minutes=0) -> Notification:
    n = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        type="SYSTEM",
        title=title,
        body="body",
        link=None,
        data={"k": 1},
        created_at=datetime.now(UTC) - timedelta(minutes=age_minutes),
        read_at=datetime.now(UTC) if read else None,
    )
    db.add(n)
    await db.flush()
    return n


# ---- REST ------------------------------------------------------------------------------------------
async def test_requires_auth(client):
    assert (await client.get("/api/v1/notifications")).status_code == 401
    assert (await client.get("/api/v1/notifications/unread-count")).status_code == 401


async def test_list_is_own_newest_first_and_paginated(client, db):
    me = await make_student(db)
    other = await make_student(db)
    for i in range(3):
        await _make_notification(db, me.id, f"n{i}", age_minutes=10 - i)
    await _make_notification(db, other.id, "not mine")

    r = await client.get("/api/v1/notifications", headers=auth_headers(me))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3 and body["page"] == 1 and body["pages"] == 1
    assert [i["title"] for i in body["items"]] == ["n2", "n1", "n0"]
    item = body["items"][0]
    assert set(item) == {"id", "type", "title", "body", "link", "data", "read_at", "created_at"}
    assert item["data"] == {"k": 1} and item["read_at"] is None and item["created_at"].endswith("Z")

    r = await client.get("/api/v1/notifications?page=2&page_size=2", headers=auth_headers(me))
    assert r.json()["total"] == 3 and len(r.json()["items"]) == 1 and r.json()["pages"] == 2


async def test_unread_only_filter_and_count(client, db):
    me = await make_student(db)
    await _make_notification(db, me.id, "unread")
    await _make_notification(db, me.id, "read", read=True)

    r = await client.get("/api/v1/notifications?unread_only=true", headers=auth_headers(me))
    assert [i["title"] for i in r.json()["items"]] == ["unread"]
    r = await client.get("/api/v1/notifications/unread-count", headers=auth_headers(me))
    assert r.status_code == 200 and r.json() == {"count": 1}


async def test_mark_read_updates_row_and_publishes_unread_count(client, db, captured):
    me = await make_student(db)
    n1 = await _make_notification(db, me.id, "a")
    await _make_notification(db, me.id, "b")

    r = await client.post(f"/api/v1/notifications/{n1.id}/read", headers=auth_headers(me))
    assert r.status_code == 200
    assert r.json()["read_at"] is not None
    assert (await client.get("/api/v1/notifications/unread-count", headers=auth_headers(me))).json() == {"count": 1}
    assert (me.id, {"type": "unread_count", "data": {"count": 1}}) in captured.messages

    # idempotent: second call keeps the original timestamp and publishes nothing new
    before = len(captured.messages)
    first_read_at = r.json()["read_at"]
    r2 = await client.post(f"/api/v1/notifications/{n1.id}/read", headers=auth_headers(me))
    assert r2.status_code == 200 and r2.json()["read_at"] == first_read_at
    assert len(captured.messages) == before


async def test_read_all(client, db, captured):
    me = await make_student(db)
    other = await make_student(db)
    for _ in range(3):
        await _make_notification(db, me.id)
    theirs = await _make_notification(db, other.id)

    r = await client.post("/api/v1/notifications/read-all", headers=auth_headers(me))
    assert r.status_code == 200 and "3" in r.json()["message"]
    assert (await client.get("/api/v1/notifications/unread-count", headers=auth_headers(me))).json() == {"count": 0}
    assert (me.id, {"type": "unread_count", "data": {"count": 0}}) in captured.messages
    await db.refresh(theirs)
    assert theirs.read_at is None  # other users untouched


async def test_delete_own_only(client, db):
    me = await make_student(db)
    other = await make_student(db)
    mine = await _make_notification(db, me.id)
    theirs = await _make_notification(db, other.id)

    assert (await client.delete(f"/api/v1/notifications/{theirs.id}", headers=auth_headers(me))).status_code == 404
    assert (await client.post(f"/api/v1/notifications/{theirs.id}/read", headers=auth_headers(me))).status_code == 404
    assert (await client.delete(f"/api/v1/notifications/{mine.id}", headers=auth_headers(me))).status_code == 204
    r = await client.get("/api/v1/notifications", headers=auth_headers(me))
    assert r.json()["total"] == 0
    assert (await client.delete(f"/api/v1/notifications/{mine.id}", headers=auth_headers(me))).status_code == 404
    assert (await client.delete(f"/api/v1/notifications/{uuid.uuid4()}", headers=auth_headers(me))).status_code == 404


async def test_notify_creates_row_and_stages_publish(db, captured, monkeypatch):
    """side_effects.notify (used by every domain module) -> row + websocket notification + unread_count."""
    monkeypatch.setattr(side_effects, "dispatcher", captured)
    user = await make_student(db)
    n = side_effects.notify(db, user.id, "APPLICATION_STATUS", "Status changed", "Shortlisted", link="/x", data={"a": 1})
    await db.flush()
    await side_effects.flush(db)

    assert (await db.get(Notification, n.id)) is not None
    kinds = [m["type"] for uid, m in captured.messages if uid == user.id]
    assert kinds == ["notification", "unread_count"]
    assert captured.notifications[0]["title"] == "Status changed"
    assert captured.messages[1][1]["data"] == {"count": 1}


# ---- WebSocket -------------------------------------------------------------------------------------
class FakeWebSocket:
    """Just enough of Starlette's WebSocket for ``ws.websocket_endpoint`` (runs on the test's event loop)."""

    def __init__(self) -> None:
        self.accepted = False
        self.closed_code: int | None = None
        self.sent: list[dict[str, Any]] = []
        self._incoming: asyncio.Queue[str | None] = asyncio.Queue()
        self._sent_event = asyncio.Event()

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: Any) -> None:
        self.sent.append(data)
        self._sent_event.set()

    async def send_text(self, data: str) -> None:
        await self.send_json(json.loads(data))

    async def receive_text(self) -> str:
        msg = await self._incoming.get()
        if msg is None:
            raise WebSocketDisconnect(1000)
        return msg

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        if self.closed_code is None:
            self.closed_code = code
            await self._incoming.put(None)  # unblock receive_text like a real close would

    # test helpers
    async def client_sends(self, payload: dict[str, Any]) -> None:
        await self._incoming.put(json.dumps(payload))

    async def client_disconnects(self) -> None:
        await self._incoming.put(None)

    async def wait_for(self, predicate, timeout: float = 5.0) -> None:
        async def _loop() -> None:
            while not any(predicate(m) for m in self.sent):
                self._sent_event.clear()
                if any(predicate(m) for m in self.sent):
                    return
                await self._sent_event.wait()

        await asyncio.wait_for(_loop(), timeout)


@pytest.fixture
def ws_db(db, db_conn, monkeypatch):
    """The websocket authenticates through ``ws.SessionLocal``: point it at the test connection."""

    def factory() -> AsyncSession:
        return AsyncSession(bind=db_conn, join_transaction_mode="create_savepoint", expire_on_commit=False)

    monkeypatch.setattr(ws, "SessionLocal", factory)
    return db


async def _subscribers(user_id) -> int:
    res = await redis_core.get_redis().pubsub_numsub(f"user:{user_id}")
    return int(res[0][1])


@pytest.mark.parametrize("token", [None, "", "garbage"])
async def test_ws_rejects_missing_or_bad_token_with_4401(ws_db, token):
    sock = FakeWebSocket()
    await ws.websocket_endpoint(sock, token)  # type: ignore[arg-type]
    assert sock.accepted and sock.closed_code == 4401 and sock.sent == []


async def test_ws_rejects_expired_token(ws_db):
    user = await make_student(ws_db)
    token, _ = create_access_token(user.id, user.role, ttl_seconds=-5)
    sock = FakeWebSocket()
    await ws.websocket_endpoint(sock, token)  # type: ignore[arg-type]
    assert sock.closed_code == 4401


async def test_ws_rejects_unknown_and_inactive_user(ws_db):
    inactive = await make_user(ws_db, "STUDENT", is_active=False)
    for uid in (uuid.uuid4(), inactive.id):
        token, _ = create_access_token(uid, "STUDENT")
        sock = FakeWebSocket()
        await ws.websocket_endpoint(sock, token)  # type: ignore[arg-type]
        assert sock.closed_code == 4401


async def test_ws_fan_out_from_redis_and_cleanup(ws_db):
    user = await make_student(ws_db)
    other = await make_student(ws_db)
    await _make_notification(ws_db, user.id)
    await ws_db.flush()
    token, _ = create_access_token(user.id, user.role)

    sock = FakeWebSocket()
    task = asyncio.create_task(ws.websocket_endpoint(sock, token))  # type: ignore[arg-type]
    try:
        # initial state: current unread count
        await sock.wait_for(lambda m: m["type"] == "unread_count")
        assert sock.sent[0] == {"type": "unread_count", "data": {"count": 1}}
        assert await _subscribers(user.id) == 1

        payload = {"type": "notification", "data": {"id": str(uuid.uuid4()), "title": "Live"}}
        await redis_core.publish(f"user:{user.id}", payload)
        await redis_core.publish(f"user:{other.id}", {"type": "notification", "data": {"title": "not for me"}})
        await redis_core.publish(f"user:{user.id}", {"type": "job", "data": {"id": "j1", "status": "RUNNING"}})
        await sock.wait_for(lambda m: m["type"] == "job")
        assert payload in sock.sent
        assert not any(m.get("data", {}).get("title") == "not for me" for m in sock.sent)

        await sock.client_sends({"type": "pong"})  # accepted silently
        await sock.client_disconnects()
        await asyncio.wait_for(task, 5)
    finally:
        if not task.done():
            task.cancel()
    assert await _subscribers(user.id) == 0  # pub/sub subscription released


async def test_ws_ping_and_heartbeat_timeout(ws_db, monkeypatch):
    monkeypatch.setattr(ws, "PING_INTERVAL_SECONDS", 0.05)
    user = await make_student(ws_db)
    token, _ = create_access_token(user.id, user.role)
    sock = FakeWebSocket()
    task = asyncio.create_task(ws.websocket_endpoint(sock, token))  # type: ignore[arg-type]
    try:
        await sock.wait_for(lambda m: m["type"] == "ping")
        await asyncio.wait_for(task, 5)  # never answered with pong -> server gives up
    finally:
        if not task.done():
            task.cancel()
    assert sock.closed_code == 1011
    assert sum(1 for m in sock.sent if m["type"] == "ping") == ws.MAX_MISSED_PONGS


async def test_ws_closes_4401_when_token_expires(ws_db):
    user = await make_student(ws_db)
    token, _ = create_access_token(user.id, user.role, ttl_seconds=2)
    sock = FakeWebSocket()
    task = asyncio.create_task(ws.websocket_endpoint(sock, token))  # type: ignore[arg-type]
    try:
        await sock.wait_for(lambda m: m["type"] == "unread_count")
        await asyncio.wait_for(task, 5)
    finally:
        if not task.done():
            task.cancel()
    assert sock.closed_code == 4401
