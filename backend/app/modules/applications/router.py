import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from app.core.db import DB
from app.core.deps import CurrentUser, Pagination, require_roles
from app.core.pagination import Page
from app.modules.applications import schemas as s
from app.modules.applications import service
from app.modules.users.models import User

router = APIRouter(prefix="/applications", tags=["applications"])

StudentUser = Annotated[User, Depends(require_roles("STUDENT"))]
StaffUser = Annotated[User, Depends(require_roles("ADMIN", "FACULTY", "COMPANY"))]


async def _detail(db, user: User, application, status_code: int = 200) -> JSONResponse:
    """Serialise ``ApplicationDetail``; interview ``comments`` are omitted entirely for STUDENT viewers."""
    detail = await service.build_detail(db, user, application)
    payload = detail.model_dump(mode="json")
    if user.role == "STUDENT":
        for iv in payload["interviews"]:
            iv.pop("comments", None)
    return JSONResponse(payload, status_code=status_code)


@router.post("", response_model=s.ApplicationDetail, status_code=status.HTTP_201_CREATED)
async def create_application(db: DB, user: StudentUser, body: s.ApplicationCreateRequest):
    a = await service.submit(db, user, body)
    return await _detail(db, user, a, 201)


@router.get("", response_model=Page[s.ApplicationSummary])
async def list_applications(
    db: DB,
    user: CurrentUser,
    pagination: Pagination,
    status: Annotated[list[str] | None, Query()] = None,
    internship_id: uuid.UUID | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
):
    return await service.list_applications(db, user, pagination, statuses=status, internship_id=internship_id, q=q)


# NOTE: static path declared before /{application_id}
@router.post("/bulk-status", response_model=s.BulkStatusResult)
async def bulk_status(db: DB, user: StaffUser, body: s.BulkStatusRequest):
    return await service.bulk_status(db, user, body)


@router.get("/{application_id}", response_model=s.ApplicationDetail)
async def get_application(db: DB, user: CurrentUser, application_id: uuid.UUID):
    a = await service.get_visible(db, user, application_id)
    return await _detail(db, user, a)


@router.patch("/{application_id}/status", response_model=s.ApplicationDetail)
async def update_status(db: DB, user: StaffUser, application_id: uuid.UUID, body: s.ApplicationStatusUpdateRequest):
    a = await service.update_status(db, user, application_id, body)
    return await _detail(db, user, a)


@router.post("/{application_id}/withdraw", response_model=s.ApplicationDetail)
async def withdraw(db: DB, user: StudentUser, application_id: uuid.UUID, body: s.WithdrawRequest | None = None):
    a = await service.withdraw(db, user, application_id, body.reason if body else None)
    return await _detail(db, user, a)


@router.delete("/{application_id}", response_model=s.ApplicationDetail)
async def delete_application(db: DB, user: StudentUser, application_id: uuid.UUID):
    """Spec "Delete: Withdraw": alias of POST /{id}/withdraw."""
    a = await service.withdraw(db, user, application_id, None)
    return await _detail(db, user, a)


@router.post("/{application_id}/complete", response_model=s.ApplicationDetail)
async def complete(db: DB, user: StaffUser, application_id: uuid.UUID):
    a = await service.complete(db, user, application_id)
    return await _detail(db, user, a)


@router.get("/{application_id}/resume-url", response_model=s.ResumeUrl)
async def resume_url(db: DB, user: CurrentUser, application_id: uuid.UUID):
    return await service.resume_url(db, user, application_id)
