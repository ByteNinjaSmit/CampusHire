"""Reports endpoints (plan 4.4): list, JSON report, async export; plus /jobs."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.deps import CurrentUser, Pagination
from app.core.db import DB
from app.core.pagination import Page
from app.core.storage import DOWNLOAD_TTL_SECONDS, Storage, get_storage
from app.core.errors import not_found
from app.modules.reports import service
from app.modules.reports.schemas import ExportRequest, JobOut, ReportData, ReportMeta

router = APIRouter(prefix="/reports", tags=["reports"])
jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[ReportMeta])
async def list_reports(user: CurrentUser) -> list[ReportMeta]:
    """Reports available to the caller's role."""
    return service.list_reports(user)


@router.get("/{key}", response_model=ReportData)
async def get_report(
    key: str,
    db: DB,
    user: CurrentUser,
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: date | None = None,
    internship_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
) -> ReportData:
    params: dict[str, Any] = {
        "from": from_,
        "to": to,
        "internship_id": internship_id,
        "company_id": company_id,
        "student_id": student_id,
    }
    return await service.build_report(db, user, key, {k: v for k, v in params.items() if v is not None})


@router.post("/{key}/export", response_model=JobOut, status_code=202)
async def export_report(key: str, body: ExportRequest, db: DB, user: CurrentUser) -> JobOut:
    """Queue a PDF/XLSX export (Celery task ``reports.export``); poll ``GET /jobs/{id}``."""
    job = await service.create_export_job(db, user, key, body.format, body.params)
    return service.job_out(job)


@jobs_router.get("", response_model=Page[JobOut])
async def list_jobs(
    db: DB,
    user: CurrentUser,
    pagination: Pagination,
    store: Annotated[Storage, Depends(get_storage)],
    type: str | None = None,  # noqa: A002 - query param name fixed by the API contract
):
    return await service.list_jobs(db, user, type, pagination, store)


@jobs_router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: uuid.UUID, db: DB, user: CurrentUser, store: Annotated[Storage, Depends(get_storage)]
) -> JobOut:
    job = await service.get_job_for(db, user, job_id)
    return await service.to_job_out(db, job, store)


class DownloadUrl(BaseModel):
    url: str
    expires_in: int


@jobs_router.get("/{job_id}/download-url", response_model=DownloadUrl)
async def job_download_url(
    job_id: uuid.UUID, db: DB, user: CurrentUser, store: Annotated[Storage, Depends(get_storage)]
) -> DownloadUrl:
    """Presigned GET (5 min) for a finished export."""
    job = await service.get_job_for(db, user, job_id)
    url = await service.download_url_for(db, job, store)
    if url is None:
        raise not_found("No file available for this job")
    return DownloadUrl(url=url, expires_in=DOWNLOAD_TTL_SECONDS)
