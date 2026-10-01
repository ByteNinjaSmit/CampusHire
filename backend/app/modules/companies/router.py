import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.db import DB
from app.core.deps import AdminUser, CurrentUser, Pagination, require_roles
from app.core.pagination import Page
from app.core.storage import Storage, get_storage
from app.core.types import CompanyStatus
from app.modules.companies import schemas as s
from app.modules.companies import service
from app.modules.users.models import User

router = APIRouter(prefix="/companies", tags=["companies"])

StorageDep = Annotated[Storage, Depends(get_storage)]
AdminOrFaculty = Annotated[User, Depends(require_roles("ADMIN", "FACULTY"))]
CompanyEditor = Annotated[User, Depends(require_roles("ADMIN", "FACULTY", "COMPANY"))]
AdminOrCompany = Annotated[User, Depends(require_roles("ADMIN", "COMPANY"))]


@router.get("", response_model=Page[s.CompanySummary])
async def list_companies(
    db: DB,
    user: CurrentUser,
    storage: StorageDep,
    pagination: Pagination,
    q: Annotated[str | None, Query(max_length=100)] = None,
    location: Annotated[str | None, Query(max_length=100)] = None,
    industry: Annotated[str | None, Query(max_length=80)] = None,
    status: Annotated[CompanyStatus | None, Query()] = None,
):
    return await service.list_companies(
        db, storage, user, pagination, q, location, industry, status.value if status else None
    )


@router.post("", response_model=s.Company, status_code=status.HTTP_201_CREATED)
async def create_company(db: DB, user: AdminOrFaculty, storage: StorageDep, body: s.CompanyCreateRequest):
    return await service.create_company(db, storage, user, body)


@router.get("/{company_id}", response_model=s.Company)
async def get_company(db: DB, user: CurrentUser, storage: StorageDep, company_id: uuid.UUID):
    return await service.get_company(db, storage, user, company_id)


@router.patch("/{company_id}", response_model=s.Company)
async def update_company(
    db: DB, user: CompanyEditor, storage: StorageDep, company_id: uuid.UUID, body: s.CompanyUpdateRequest
):
    return await service.update_company(db, storage, user, company_id, body)


@router.post("/{company_id}/approve", response_model=s.Company)
async def approve_company(db: DB, admin: AdminUser, storage: StorageDep, company_id: uuid.UUID):
    return await service.approve(db, storage, admin, company_id)


@router.post("/{company_id}/archive", response_model=s.Company)
async def archive_company(db: DB, admin: AdminUser, storage: StorageDep, company_id: uuid.UUID):
    return await service.archive(db, storage, admin, company_id)


@router.post("/{company_id}/restore", response_model=s.Company)
async def restore_company(db: DB, admin: AdminUser, storage: StorageDep, company_id: uuid.UUID):
    return await service.restore(db, storage, admin, company_id)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(db: DB, admin: AdminUser, company_id: uuid.UUID):
    await service.delete_company(db, admin, company_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{company_id}/internships", response_model=Page[s.CompanyInternshipItem])
async def company_internships(
    db: DB, user: CurrentUser, storage: StorageDep, pagination: Pagination, company_id: uuid.UUID
):
    return await service.list_internships(db, storage, user, company_id, pagination)


@router.get("/{company_id}/ratings", response_model=s.CompanyRatingsResponse)
async def company_ratings(db: DB, user: CurrentUser, company_id: uuid.UUID):
    return await service.ratings(db, user, company_id)


@router.get("/{company_id}/members", response_model=list[s.CompanyMember])
async def company_members(db: DB, user: AdminOrCompany, company_id: uuid.UUID):
    return await service.list_members(db, user, company_id)
