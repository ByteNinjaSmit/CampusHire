"""WebSocket ``/api/v1/ws?token=<access_jwt>`` (plan 6.10).

* auth: access JWT in the query string; bad / expired token -> accept, then close with 4401 (so browsers
  see the close code instead of a bare HTTP 403). The socket is also closed with 4401 when the token expires,
  so the client refreshes and reconnects.
* one Redis pub/sub subscription per socket on ``user:{id}``; messages published by ``side_effects.flush``
  and by workers are forwarded verbatim.
* server ``{"type":"ping"}`` every 25 s, client answers ``{"type":"pong"}``; no pong for 2 pings -> closed.
"""

import asyncio
import contextlib
import json
import logging
import time
import uuid
from typing import NamedTuple

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.errors import AppError
from app.core.redis import get_redis
from app.core.security import decode_access_token
from app.modules.notifications import repository as repo
from app.modules.users.models import User

log = logging.getLogger(__name__)

router = APIRouter(tags=["realtime"])

PING_INTERVAL_SECONDS = 25
MAX_MISSED_PONGS = 2
CLOSE_UNAUTHORIZED = 4401


class _Auth(NamedTuple):
    user_id: uuid.UUID
    exp: float
    unread: int


async def _authenticate(token: str | None) -> _Auth | None:
    """Validate the token and that the user is still active; None when the socket must be refused."""
    if not token:
        return None
    try:
        claims = decode_access_token(token)
        user_id = uuid.UUID(claims["sub"])
    except (AppError, ValueError, KeyError):
        return None
    async with SessionLocal() as session:
        active = (await session.execute(select(User.is_active).where(User.id == user_id))).scalar_one_or_none()
        if not active:
            return None
        count = await repo.unread_count(session, user_id)
    return _Auth(user_id, float(claims["exp"]), count)


async def _forward(ws: WebSocket, pubsub) -> None:
    while True:
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if msg is None:
            continue
        data = msg.get("data")
        if isinstance(data, bytes):
            data = data.decode()
        await ws.send_text(data)


async def _heartbeat(ws: WebSocket, state: dict[str, int]) -> None:
    while True:
        await asyncio.sleep(PING_INTERVAL_SECONDS)
        if state["missed"] >= MAX_MISSED_PONGS:
            await ws.close(code=1011, reason="heartbeat timeout")
            return
        state["missed"] += 1
        await ws.send_json({"type": "ping"})


async def _receive(ws: WebSocket, state: dict[str, int]) -> None:
    while True:
        raw = await ws.receive_text()
        try:
            msg = json.loads(raw)
        except ValueError:
            continue
        if isinstance(msg, dict) and msg.get("type") == "pong":
            state["missed"] = 0


async def _expire_at(ws: WebSocket, exp: float) -> None:
    await asyncio.sleep(max(0.0, exp - time.time()))
    await ws.close(code=CLOSE_UNAUTHORIZED, reason="token expired")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None) -> None:
    await websocket.accept()
    auth = await _authenticate(token)
    if auth is None:
        await websocket.close(code=CLOSE_UNAUTHORIZED, reason="invalid or expired token")
        return
    user_id, exp, unread = auth

    pubsub = get_redis().pubsub()
    try:
        await pubsub.subscribe(f"user:{user_id}")
        await websocket.send_json({"type": "unread_count", "data": {"count": unread}})
        state = {"missed": 0}
        tasks = [
            asyncio.create_task(_forward(websocket, pubsub)),
            asyncio.create_task(_heartbeat(websocket, state)),
            asyncio.create_task(_receive(websocket, state)),
            asyncio.create_task(_expire_at(websocket, exp)),
        ]
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in done:
                exc = t.exception()
                if exc is not None and not isinstance(exc, WebSocketDisconnect | RuntimeError):
                    log.warning("websocket task ended with %r", exc)
        finally:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe(f"user:{user_id}")
            await pubsub.aclose()
        with contextlib.suppress(Exception):
            await websocket.close()
