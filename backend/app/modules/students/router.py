import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.db import DB
from app.core.deps import AdminUser, Pagination, require_roles
from app.core.pagination import Page
from app.core.storage import Storage, get_storage
from app.modules.auth.schemas import MessageResponse
from app.modules.students import schemas as s
from app.modules.students import service
from app.modules.users.models import User

router = APIRouter(prefix="/students", tags=["students"])

StorageDep = Annotated[Storage, Depends(get_storage)]
StudentUser = Annotated[User, Depends(require_roles("STUDENT"))]
StaffUser = Annotated[User, Depends(require_roles("ADMIN", "FACULTY"))]
StaffOrCompany = Annotated[User, Depends(require_roles("ADMIN", "FACULTY", "COMPANY"))]
AdminOrStudent = Annotated[User, Depends(require_roles("ADMIN", "STUDENT"))]


@router.get("", response_model=Page[s.StudentListItem])
async def list_students(
    db: DB,
    viewer: StaffUser,
    pagination: Pagination,
    q: Annotated[str | None, Query(max_length=100)] = None,
    department: Annotated[str | None, Query(max_length=80)] = None,
    gpa_min: Annotated[float | None, Query(ge=0, le=4)] = None,
    gpa_max: Annotated[float | None, Query(ge=0, le=4)] = None,
):
    return await service.list_students(db, viewer, pagination, q, department, gpa_min, gpa_max)


# NOTE: static paths (/me) must be declared before /{student_id}
@router.get("/me", response_model=s.StudentMe)
async def get_me(db: DB, user: StudentUser):
    return await service.get_me(db, user)


@router.patch("/me", response_model=s.StudentMe)
async def update_me(db: DB, user: StudentUser, body: s.StudentProfileUpdate):
    return await service.update_me(db, user, body)


@router.put("/me/resume", response_model=s.StudentMe)
async def set_resume(db: DB, user: StudentUser, body: s.ResumeSelect):
    return await service.set_default_resume(db, user, body.document_id)


@router.get("/{student_id}", response_model=s.StudentDetail)
async def get_student(db: DB, viewer: StaffOrCompany, student_id: uuid.UUID):
    return await service.get_student(db, viewer, student_id)


@router.patch("/{student_id}", response_model=s.StudentDetail)
async def update_student(db: DB, admin: AdminUser, student_id: uuid.UUID, body: s.AdminStudentUpdate):
    return await service.admin_update(db, admin, student_id, body)


@router.post("/{student_id}/deactivate", response_model=MessageResponse)
async def deactivate_student(db: DB, admin: AdminUser, student_id: uuid.UUID, body: s.DeactivateIn):
    return await service.deactivate(db, admin, student_id, body.reason)


@router.get("/{student_id}/applications", response_model=Page[s.ApplicationSummary])
async def student_applications(
    db: DB, viewer: AdminOrStudent, storage: StorageDep, pagination: Pagination, student_id: uuid.UUID
):
    return await service.application_history(db, storage, viewer, student_id, pagination)
