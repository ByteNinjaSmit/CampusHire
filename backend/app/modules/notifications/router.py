import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.core.db import DB
from app.core.deps import CurrentUser, Pagination
from app.core.pagination import Page
from app.modules.notifications import service
from app.modules.notifications.schemas import MessageResponse, NotificationOut, UnreadCount

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Page[NotificationOut])
async def list_notifications(
    db: DB, user: CurrentUser, pagination: Pagination, unread_only: Annotated[bool, Query()] = False
):
    return await service.list_notifications(db, user.id, pagination, unread_only)


# NOTE: static paths must be declared before /{notification_id}
@router.get("/unread-count", response_model=UnreadCount)
async def unread_count(db: DB, user: CurrentUser):
    return UnreadCount(count=await service.unread_count(db, user.id))


@router.post("/read-all", response_model=MessageResponse)
async def read_all(db: DB, user: CurrentUser):
    changed = await service.mark_all_read(db, user.id)
    return MessageResponse(message=f"{changed} notification(s) marked as read")


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(db: DB, user: CurrentUser, notification_id: uuid.UUID):
    return NotificationOut.model_validate(await service.mark_read(db, user.id, notification_id))


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(db: DB, user: CurrentUser, notification_id: uuid.UUID):
    await service.delete(db, user.id, notification_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
