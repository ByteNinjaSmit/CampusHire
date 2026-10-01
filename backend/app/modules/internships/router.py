import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from app.core.db import DB
from app.core.deps import AdminUser, CurrentUser, Pagination, require_roles
from app.core.pagination import Page
from app.modules.applications.schemas import ApplicationSummary
from app.modules.internships import repository as repo
from app.modules.internships import schemas as s
from app.modules.internships import service
from app.modules.users.models import User

router = APIRouter(prefix="/internships", tags=["internships"])

StaffUser = Annotated[User, Depends(require_roles("ADMIN", "FACULTY", "COMPANY"))]
StudentUser = Annotated[User, Depends(require_roles("STUDENT"))]


def search_filters(
    q: Annotated[str | None, Query(max_length=200)] = None,
    domain: Annotated[list[str] | None, Query()] = None,
    company_id: Annotated[list[uuid.UUID] | None, Query()] = None,
    location: Annotated[str | None, Query(max_length=160)] = None,
    work_mode: Annotated[list[Literal["ONSITE", "REMOTE", "HYBRID"]] | None, Query()] = None,
    stipend_min: Annotated[Decimal | None, Query(ge=0)] = None,
    stipend_max: Annotated[Decimal | None, Query(ge=0)] = None,
    duration_min: Annotated[int | None, Query(ge=1)] = None,
    duration_max: Annotated[int | None, Query(le=52)] = None,
    skills: Annotated[list[str] | None, Query()] = None,
    deadline_before: Annotated[datetime | None, Query()] = None,
    deadline_after: Annotated[datetime | None, Query()] = None,
    status: Annotated[list[str] | None, Query()] = None,
    mine: bool = False,
    include_archived: bool = False,
    sort: Literal["relevance", "newest", "stipend_desc", "deadline_asc"] = "relevance",
) -> repo.SearchFilters:
    return repo.SearchFilters(
        q=q,
        domain=domain or [],
        company_id=company_id or [],
        location=location,
        work_mode=list(work_mode or []),
        stipend_min=stipend_min,
        stipend_max=stipend_max,
        duration_min=duration_min,
        duration_max=duration_max,
        skills=skills or [],
        deadline_before=deadline_before,
        deadline_after=deadline_after,
        status=status or [],
        mine=mine,
        include_archived=include_archived,
        sort=sort,
    )


Filters = Annotated[repo.SearchFilters, Depends(search_filters)]


# NOTE: static paths (/facets, /saved, /recommended, /bulk) are declared before /{internship_id}
@router.get("", response_model=Page[s.InternshipSummary])
async def list_internships(db: DB, user: CurrentUser, filters: Filters, pagination: Pagination):
    return await service.list_internships(db, user, filters, pagination)


@router.get("/facets", response_model=s.InternshipFacets)
async def facets(db: DB, user: CurrentUser, filters: Filters):
    return await service.facets(db, user, filters)


@router.get("/saved", response_model=Page[s.InternshipSummary])
async def saved(db: DB, user: StudentUser, pagination: Pagination):
    return await service.saved(db, user, pagination)


@router.get("/recommended", response_model=list[s.InternshipSummary])
async def recommended(db: DB, user: StudentUser, limit: Annotated[int, Query(ge=1, le=50)] = 6):
    return await service.recommended(db, user, limit)


@router.post("", response_model=s.Internship, status_code=status.HTTP_201_CREATED)
async def create_internship(db: DB, user: StaffUser, body: s.InternshipCreateRequest):
    i = await service.create(db, user, body)
    return await service.to_detail(db, user, i)


@router.post("/bulk", response_model=s.BulkActionResult)
async def bulk(db: DB, admin: AdminUser, body: s.BulkInternshipAction):
    return await service.bulk(db, admin, body)


@router.get("/{internship_id}", response_model=s.Internship)
async def get_internship(db: DB, user: CurrentUser, internship_id: uuid.UUID):
    return await service.get_detail(db, user, internship_id)


@router.patch("/{internship_id}", response_model=s.Internship)
async def update_internship(db: DB, user: StaffUser, internship_id: uuid.UUID, body: s.InternshipUpdateRequest):
    i = await service.update(db, user, internship_id, body)
    return await service.to_detail(db, user, i)


@router.post("/{internship_id}/submit", response_model=s.Internship)
async def submit_internship(db: DB, user: StaffUser, internship_id: uuid.UUID):
    return await service.to_detail(db, user, await service.submit(db, user, internship_id))


@router.post("/{internship_id}/approve", response_model=s.Internship)
async def approve_internship(db: DB, admin: AdminUser, internship_id: uuid.UUID):
    return await service.to_detail(db, admin, await service.approve(db, admin, internship_id))


@router.post("/{internship_id}/reject", response_model=s.Internship)
async def reject_internship(db: DB, admin: AdminUser, internship_id: uuid.UUID, body: s.RejectRequest):
    return await service.to_detail(db, admin, await service.reject(db, admin, internship_id, body.reason))


@router.post("/{internship_id}/close", response_model=s.Internship)
async def close_internship(db: DB, user: StaffUser, internship_id: uuid.UUID):
    return await service.to_detail(db, user, await service.close(db, user, internship_id))


@router.post("/{internship_id}/archive", response_model=s.Internship)
async def archive_internship(db: DB, user: StaffUser, internship_id: uuid.UUID):
    return await service.to_detail(db, user, await service.archive(db, user, internship_id))


@router.post("/{internship_id}/restore", response_model=s.Internship)
async def restore_internship(db: DB, admin: AdminUser, internship_id: uuid.UUID):
    return await service.to_detail(db, admin, await service.restore(db, admin, internship_id))


@router.delete("/{internship_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_internship(db: DB, admin: AdminUser, internship_id: uuid.UUID):
    await service.delete(db, admin, internship_id)


@router.post("/{internship_id}/save", response_model=s.SaveResult)
async def save_internship(db: DB, user: StudentUser, internship_id: uuid.UUID):
    await service.save(db, user, internship_id)
    return s.SaveResult(is_saved=True)


@router.delete("/{internship_id}/save", response_model=s.SaveResult)
async def unsave_internship(db: DB, user: StudentUser, internship_id: uuid.UUID):
    await service.unsave(db, user, internship_id)
    return s.SaveResult(is_saved=False)


@router.get("/{internship_id}/similar", response_model=list[s.InternshipSummary])
async def similar_internships(
    db: DB, user: CurrentUser, internship_id: uuid.UUID, limit: Annotated[int, Query(ge=1, le=50)] = 6
):
    return await service.similar(db, user, internship_id, limit)


@router.get("/{internship_id}/applications", response_model=Page[ApplicationSummary])
async def internship_applications(
    db: DB,
    user: StaffUser,
    internship_id: uuid.UUID,
    pagination: Pagination,
    status: Annotated[list[str] | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
):
    return await service.list_applications(db, user, internship_id, status or [], q, pagination)
