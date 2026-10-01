import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, PlainSerializer


def _iso_z(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


UtcDateTime = Annotated[datetime, PlainSerializer(_iso_z, return_type=str, when_used="json")]


class NotificationOut(BaseModel):
    """Plan 6.9 ``Notification``. Mirrors the payload ``side_effects.notify`` pushes over the websocket."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    title: str
    body: str
    link: str | None
    data: dict[str, Any]
    read_at: UtcDateTime | None
    created_at: UtcDateTime


class UnreadCount(BaseModel):
    count: int


class MessageResponse(BaseModel):
    message: str
