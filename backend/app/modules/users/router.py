import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.db import DB
from app.core.deps import AdminUser, CurrentUser, Pagination
from app.core.pagination import Page
from app.modules.users import schemas as s
from app.modules.users import service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=Page[s.UserSummary])
async def list_users(
    db: DB,
    admin: AdminUser,
    pagination: Pagination,
    role: Annotated[s.Role | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    is_active: Annotated[bool | None, Query()] = None,
):
    return await service.list_users(db, pagination, role.value if role else None, q, is_active)


@router.post("", response_model=s.UserDetail, status_code=status.HTTP_201_CREATED)
async def create_user(db: DB, admin: AdminUser, body: s.AdminCreateUserRequest):
    user = await service.create_user(db, admin, body)
    return await service.build_detail(db, user)


# NOTE: static paths (/me, /bulk) must be declared before /{user_id}
@router.patch("/me", response_model=s.Me)
async def update_me(db: DB, user: CurrentUser, body: s.UpdateMeRequest):
    user = await service.update_me(db, user, body)
    return await service.build_me(db, user)


@router.post("/bulk", response_model=s.BulkActionResult)
async def bulk(db: DB, admin: AdminUser, body: s.BulkUserAction):
    return await service.bulk_action(db, admin, body)


@router.get("/{user_id}", response_model=s.UserDetail)
async def get_user(db: DB, admin: AdminUser, user_id: uuid.UUID):
    return await service.build_detail(db, await service.get_user_or_404(db, user_id))


@router.patch("/{user_id}", response_model=s.UserDetail)
async def update_user(db: DB, admin: AdminUser, user_id: uuid.UUID, body: s.UpdateUserRequest):
    user = await service.update_user(db, admin, user_id, body)
    return await service.build_detail(db, user)


@router.post("/{user_id}/deactivate", response_model=s.UserSummary)
async def deactivate(db: DB, admin: AdminUser, user_id: uuid.UUID, body: s.DeactivateRequest):
    return service.summary_of(await service.deactivate_user(db, admin, user_id, body.reason))


@router.post("/{user_id}/activate", response_model=s.UserSummary)
async def activate(db: DB, admin: AdminUser, user_id: uuid.UUID):
    return service.summary_of(await service.activate_user(db, admin, user_id))

