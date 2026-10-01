from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.db import DB
from app.core.deps import AdminUser, Pagination, require_roles
from app.core.pagination import Page
from app.modules.faculty import schemas as s
from app.modules.faculty import service
from app.modules.users.models import User

router = APIRouter(prefix="/faculty", tags=["faculty"])

FacultyUser = Annotated[User, Depends(require_roles("FACULTY"))]


@router.get("", response_model=Page[s.FacultyListItem])
async def list_faculty(
    db: DB, admin: AdminUser, pagination: Pagination, q: Annotated[str | None, Query(max_length=100)] = None
):
    return await service.list_faculty(db, pagination, q)


@router.get("/me", response_model=s.FacultyProfile)
async def get_me(db: DB, user: FacultyUser):
    return await service.get_me(db, user)


@router.patch("/me", response_model=s.FacultyProfile)
async def update_me(db: DB, user: FacultyUser, body: s.FacultyProfileUpdate):
    return await service.update_me(db, user, body)
