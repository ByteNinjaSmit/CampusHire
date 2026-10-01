import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.db import DB
from app.core.deps import CurrentUser, Pagination, require_roles
from app.core.pagination import Page
from app.core.types import InterviewStatus
from app.modules.interviews import schemas as s
from app.modules.interviews import service
from app.modules.users.models import User

router = APIRouter(prefix="/interviews", tags=["interviews"])

Staff = Annotated[User, Depends(require_roles("ADMIN", "FACULTY", "COMPANY"))]

# STUDENT payloads omit the internal ``comments`` field, so unset fields are excluded from the response.
_RESP = {"response_model_exclude_unset": True}


@router.post("", response_model=s.Interview, status_code=201, **_RESP)
async def create_interview(db: DB, user: Staff, body: s.InterviewCreateRequest):
    return await service.create_interview(db, user, body)


@router.get("", response_model=Page[s.Interview], **_RESP)
async def list_interviews(
    db: DB,
    user: CurrentUser,
    pagination: Pagination,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    status: Annotated[InterviewStatus | None, Query()] = None,
    application_id: Annotated[uuid.UUID | None, Query()] = None,
):
    return await service.list_interviews(
        db,
        user,
        pagination,
        date_from=date_from,
        date_to=date_to,
        status=status.value if status else None,
        application_id=application_id,
    )


@router.get("/{interview_id}", response_model=s.Interview, **_RESP)
async def get_interview(db: DB, user: CurrentUser, interview_id: uuid.UUID):
    return await service.get_interview(db, user, interview_id)


@router.patch("/{interview_id}/reschedule", response_model=s.Interview, **_RESP)
async def reschedule_interview(db: DB, user: Staff, interview_id: uuid.UUID, body: s.InterviewRescheduleRequest):
    return await service.reschedule_interview(db, user, interview_id, body)


@router.patch("/{interview_id}/result", response_model=s.Interview, **_RESP)
async def record_result(db: DB, user: Staff, interview_id: uuid.UUID, body: s.InterviewResultRequest):
    return await service.record_result(db, user, interview_id, body)


@router.post("/{interview_id}/cancel", response_model=s.Interview, **_RESP)
async def cancel_interview(db: DB, user: Staff, interview_id: uuid.UUID, body: s.InterviewCancelRequest):
    return await service.cancel_interview(db, user, interview_id, body.reason)


@router.delete("/{interview_id}", response_model=s.Interview, **_RESP)
async def delete_interview(
    db: DB, user: Staff, interview_id: uuid.UUID, reason: Annotated[str | None, Query(max_length=1000)] = None
):
    """Alias of cancel (plan 4.4)."""
    return await service.cancel_interview(db, user, interview_id, (reason or "").strip() or "Cancelled")
