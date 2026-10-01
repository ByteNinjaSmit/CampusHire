import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.db import DB
from app.core.deps import AdminUser, CurrentUser, Pagination, require_roles
from app.core.pagination import Page
from app.modules.feedback import schemas as s
from app.modules.feedback import service
from app.modules.users.models import User

router = APIRouter(prefix="/feedback", tags=["feedback"])

StudentUser = Annotated[User, Depends(require_roles("STUDENT"))]
StaffUser = Annotated[User, Depends(require_roles("ADMIN", "FACULTY", "COMPANY"))]
FacultyOrAdmin = Annotated[User, Depends(require_roles("ADMIN", "FACULTY"))]


# ---- student feedback (student -> company / internship) -----------------------------------------------
@router.post("/student", response_model=s.StudentFeedback, status_code=status.HTTP_201_CREATED)
async def create_student_feedback(db: DB, user: StudentUser, body: s.StudentFeedbackCreateRequest):
    return await service.create_student_feedback(db, user, body)


@router.get("/student", response_model=Page[s.StudentFeedback])
async def list_student_feedback(
    db: DB,
    user: CurrentUser,
    pagination: Pagination,
    company_id: Annotated[uuid.UUID | None, Query()] = None,
    internship_id: Annotated[uuid.UUID | None, Query()] = None,
):
    return await service.list_student_feedback(
        db, user, pagination, company_id=company_id, internship_id=internship_id
    )


# NOTE: static path must be declared before /student/{feedback_id}/response
@router.get("/student/trends", response_model=s.FeedbackTrends)
async def student_feedback_trends(
    db: DB,
    user: StaffUser,
    company_id: Annotated[uuid.UUID | None, Query()] = None,
    internship_id: Annotated[uuid.UUID | None, Query()] = None,
    months: Annotated[int, Query(ge=1, le=36)] = 12,
):
    return await service.student_feedback_trends(
        db, user, company_id=company_id, internship_id=internship_id, months=months
    )


@router.post("/student/{feedback_id}/response", response_model=s.StudentFeedback)
async def respond_to_student_feedback(
    db: DB, user: StaffUser, feedback_id: uuid.UUID, body: s.FeedbackResponseRequest
):
    return await service.respond_to_student_feedback(db, user, feedback_id, body.body)


# ---- company feedback (company / staff -> student) ----------------------------------------------------
@router.post("/company", response_model=s.CompanyFeedback, status_code=status.HTTP_201_CREATED)
async def create_company_feedback(db: DB, user: StaffUser, body: s.CompanyFeedbackCreateRequest):
    return await service.create_company_feedback(db, user, body)


@router.get("/company", response_model=Page[s.CompanyFeedback])
async def list_company_feedback(
    db: DB,
    user: CurrentUser,
    pagination: Pagination,
    application_id: Annotated[uuid.UUID | None, Query()] = None,
    student_id: Annotated[uuid.UUID | None, Query()] = None,
):
    return await service.list_company_feedback(
        db, user, pagination, application_id=application_id, student_id=student_id
    )


# ---- faculty feedback ---------------------------------------------------------------------------------
@router.post("/faculty", response_model=s.FacultyFeedback, status_code=status.HTTP_201_CREATED)
async def create_faculty_feedback(db: DB, user: FacultyOrAdmin, body: s.FacultyFeedbackCreateRequest):
    return await service.create_faculty_feedback(db, user, body)


@router.get("/faculty", response_model=Page[s.FacultyFeedback])
async def list_faculty_feedback(
    db: DB,
    user: FacultyOrAdmin,
    pagination: Pagination,
    internship_id: Annotated[uuid.UUID | None, Query()] = None,
):
    return await service.list_faculty_feedback(db, user, pagination, internship_id=internship_id)


# ---- system feedback ----------------------------------------------------------------------------------
@router.post("/system", response_model=s.SystemFeedback, status_code=status.HTTP_201_CREATED)
async def create_system_feedback(db: DB, user: CurrentUser, body: s.SystemFeedbackCreateRequest):
    return await service.create_system_feedback(db, user, body)


@router.get("/system", response_model=Page[s.SystemFeedback])
async def list_system_feedback(
    db: DB,
    user: CurrentUser,
    pagination: Pagination,
    type: Annotated[s.SystemType | None, Query()] = None,  # noqa: A002 - query param name from the contract
    status: Annotated[s.SystemStatus | None, Query()] = None,
):
    return await service.list_system_feedback(db, user, pagination, type_=type, status=status)


@router.get("/system/summary", response_model=s.SystemFeedbackSummary)
async def system_feedback_summary(db: DB, admin: AdminUser):
    return await service.system_feedback_summary(db)


@router.patch("/system/{feedback_id}", response_model=s.SystemFeedback)
async def update_system_feedback(db: DB, admin: AdminUser, feedback_id: uuid.UUID, body: s.SystemFeedbackUpdateRequest):
    return await service.update_system_feedback(db, admin, feedback_id, body)


@router.post(
    "/system/{feedback_id}/action-items", response_model=s.ActionItem, status_code=status.HTTP_201_CREATED
)
async def add_action_item(db: DB, admin: AdminUser, feedback_id: uuid.UUID, body: s.ActionItemCreateRequest):
    return await service.add_action_item(db, admin, feedback_id, body)


@router.patch("/action-items/{item_id}", response_model=s.ActionItem)
async def update_action_item(db: DB, admin: AdminUser, item_id: uuid.UUID, body: s.ActionItemUpdateRequest):
    return await service.update_action_item(db, admin, item_id, body)
