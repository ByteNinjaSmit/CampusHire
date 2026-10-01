import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.db import DB
from app.core.deps import CurrentUser, Pagination, require_roles
from app.core.pagination import Page
from app.modules.evaluations import schemas as s
from app.modules.evaluations import service
from app.modules.users.models import User

router = APIRouter(prefix="/evaluations", tags=["evaluations"])
forms_router = APIRouter(prefix="/evaluation-forms", tags=["evaluation-forms"])

StaffUser = Annotated[User, Depends(require_roles("ADMIN", "FACULTY", "COMPANY"))]
FormAuthor = Annotated[User, Depends(require_roles("ADMIN", "FACULTY"))]
AdminOnly = Annotated[User, Depends(require_roles("ADMIN"))]


# ---- forms --------------------------------------------------------------------------------------------
@forms_router.get("", response_model=list[s.EvaluationForm])
async def list_forms(db: DB, user: StaffUser, include_archived: Annotated[bool, Query()] = False):
    return await service.list_forms(db, include_archived)


@forms_router.post("", response_model=s.EvaluationForm, status_code=status.HTTP_201_CREATED)
async def create_form(db: DB, user: FormAuthor, body: s.EvaluationFormCreateRequest):
    return await service.create_form(db, user, body)


@forms_router.get("/{form_id}", response_model=s.EvaluationForm)
async def get_form(db: DB, user: StaffUser, form_id: uuid.UUID):
    return await service.get_form(db, form_id)


@forms_router.patch("/{form_id}", response_model=s.EvaluationForm)
async def update_form(db: DB, user: FormAuthor, form_id: uuid.UUID, body: s.EvaluationFormUpdateRequest):
    return await service.update_form(db, user, form_id, body)


@forms_router.post("/{form_id}/archive", response_model=s.EvaluationForm)
async def archive_form(db: DB, user: FormAuthor, form_id: uuid.UUID):
    return await service.archive_form(db, user, form_id)


# ---- evaluations --------------------------------------------------------------------------------------
@router.post("", response_model=s.Evaluation, status_code=status.HTTP_201_CREATED)
async def create_evaluation(db: DB, user: StaffUser, body: s.EvaluationCreateRequest):
    return await service.create_evaluation(db, user, body)


@router.get("", response_model=Page[s.Evaluation])
async def list_evaluations(
    db: DB,
    user: CurrentUser,
    pagination: Pagination,
    application_id: Annotated[uuid.UUID | None, Query()] = None,
    internship_id: Annotated[uuid.UUID | None, Query()] = None,
    student_id: Annotated[uuid.UUID | None, Query()] = None,
    include_archived: Annotated[bool, Query()] = False,
):
    return await service.list_evaluations(
        db,
        user,
        pagination,
        application_id=application_id,
        internship_id=internship_id,
        student_id=student_id,
        include_archived=include_archived,
    )


@router.get("/{evaluation_id}", response_model=s.Evaluation)
async def get_evaluation(db: DB, user: CurrentUser, evaluation_id: uuid.UUID):
    return await service.get_evaluation(db, user, evaluation_id)


@router.patch("/{evaluation_id}", response_model=s.Evaluation)
async def update_evaluation(db: DB, user: StaffUser, evaluation_id: uuid.UUID, body: s.EvaluationUpdateRequest):
    return await service.update_evaluation(db, user, evaluation_id, body)


@router.post("/{evaluation_id}/archive", response_model=s.Evaluation)
async def archive_evaluation(db: DB, user: StaffUser, evaluation_id: uuid.UUID):
    return await service.archive_evaluation(db, user, evaluation_id)


@router.delete("/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evaluation(db: DB, user: AdminOnly, evaluation_id: uuid.UUID):
    await service.delete_evaluation(db, user, evaluation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
