"""Admin endpoints (plan 4.4). Every route requires the ADMIN role.

User management lives in ``app.modules.users`` (``/users``); internship approval in ``/internships``.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status

from app.core.db import DB
from app.core.deps import AdminUser, Pagination
from app.core.errors import unprocessable
from app.core.pagination import Page
from app.core.storage import Storage, get_storage
from app.modules.admin import health, importer, service
from app.modules.admin import schemas as s

router = APIRouter(prefix="/admin", tags=["admin"])

StorageDep = Annotated[Storage, Depends(get_storage)]


# ---- system health / metrics ---------------------------------------------------------------------------------
@router.get("/health", response_model=s.HealthResponse)
async def system_health(db: DB, admin: AdminUser):
    return await health.collect_health(db)


@router.get("/metrics", response_model=s.MetricsResponse)
async def metrics(
    db: DB,
    admin: AdminUser,
    minutes: Annotated[int, Query(ge=1, le=120)] = 60,
    login_days: Annotated[int, Query(ge=1, le=90)] = 14,
):
    return await service.get_metrics(db, minutes, login_days)


# ---- audit logs ----------------------------------------------------------------------------------------------
@router.get("/audit-logs", response_model=Page[s.AuditLogOut])
async def audit_logs(
    db: DB,
    admin: AdminUser,
    pagination: Pagination,
    actor_id: Annotated[uuid.UUID | None, Query()] = None,
    entity_type: Annotated[str | None, Query(max_length=40)] = None,
    action: Annotated[str | None, Query(max_length=60)] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
):
    return await service.list_audit_logs(db, pagination, actor_id, entity_type, action, from_, to)


# ---- compliance ----------------------------------------------------------------------------------------------
@router.get("/compliance/policies", response_model=list[s.PolicyOut])
async def list_policies(db: DB, admin: AdminUser):
    return await service.list_policies(db)


@router.post("/compliance/policies", response_model=s.PolicyOut, status_code=status.HTTP_201_CREATED)
async def create_policy(db: DB, admin: AdminUser, body: s.PolicyCreate):
    return await service.create_policy(db, admin, body)


@router.patch("/compliance/policies/{policy_id}", response_model=s.PolicyOut)
async def update_policy(db: DB, admin: AdminUser, policy_id: uuid.UUID, body: s.PolicyUpdate):
    return await service.update_policy(db, admin, policy_id, body)


@router.get("/compliance/violations", response_model=Page[s.ViolationOut])
async def list_violations(
    db: DB,
    admin: AdminUser,
    pagination: Pagination,
    status: Annotated[str | None, Query(pattern="^(OPEN|RESOLVED|DISMISSED)$")] = None,
    policy_code: Annotated[str | None, Query(max_length=40)] = None,
):
    return await service.list_violations(db, pagination, status, policy_code)


@router.patch("/compliance/violations/{violation_id}", response_model=s.ViolationOut)
async def update_violation(db: DB, admin: AdminUser, violation_id: uuid.UUID, body: s.ViolationUpdate):
    return await service.update_violation(db, admin, violation_id, body)


@router.get("/compliance/documents", response_model=Page[s.DocumentQueueItem])
async def document_verification_queue(
    db: DB,
    admin: AdminUser,
    pagination: Pagination,
    verification_status: Annotated[str, Query(pattern="^(PENDING|VERIFIED|REJECTED)$")] = "PENDING",
    kind: Annotated[str | None, Query(max_length=20)] = None,
):
    """Documents awaiting verification (default PENDING). Verify with ``PATCH /documents/{id}/verification``."""
    return await service.list_document_queue(db, pagination, verification_status, kind)


@router.post("/compliance/scan", response_model=s.Job, status_code=status.HTTP_202_ACCEPTED)
async def trigger_scan(db: DB, admin: AdminUser):
    return await service.create_scan_job(db, admin)


# ---- export / import -------------------------------------------------------------------------------------------
@router.post("/export", response_model=s.Job, status_code=status.HTTP_202_ACCEPTED)
async def export_data(db: DB, admin: AdminUser, body: s.ExportRequest):
    return await service.create_export_job(db, admin, body)


@router.post("/import", response_model=s.Job, status_code=status.HTTP_202_ACCEPTED)
async def import_data(
    db: DB,
    admin: AdminUser,
    store: StorageDep,
    entity: Annotated[s.ImportEntity, Form()],
    file: Annotated[UploadFile, File()],
):
    data = await file.read(importer.MAX_IMPORT_BYTES + 1)
    return await service.create_import_job(db, admin, entity, file.filename or "", data, store)


@router.get("/import/template/{entity}")
async def import_template(admin: AdminUser, entity: str):
    if entity not in importer.ROW_MODELS:
        raise unprocessable(
            f"Unknown entity '{entity}'",
            details=[{"field": "entity", "message": f"Must be one of {', '.join(importer.ROW_MODELS)}"}],
        )
    return Response(
        content=importer.build_template(entity),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{entity}-import-template.xlsx"'},
    )


# ---- jobs (admin-run: exports, imports, compliance scans) --------------------------------------------------------
@router.get("/jobs", response_model=Page[s.Job])
async def list_jobs(
    db: DB,
    admin: AdminUser,
    pagination: Pagination,
    store: StorageDep,
    type: Annotated[str | None, Query(pattern="^(DATA_EXPORT|DATA_IMPORT|COMPLIANCE_SCAN)$")] = None,
    status: Annotated[str | None, Query(pattern="^(QUEUED|RUNNING|SUCCEEDED|FAILED)$")] = None,
):
    return await service.list_jobs(db, pagination, type, status, store)


@router.get("/jobs/{job_id}", response_model=s.Job)
async def get_job(db: DB, admin: AdminUser, job_id: uuid.UUID, store: StorageDep):
    return await service.get_job(db, job_id, store)


@router.get("/jobs/{job_id}/download", response_model=s.JobDownload)
async def download_job(db: DB, admin: AdminUser, job_id: uuid.UUID, store: StorageDep):
    return await service.get_job_download(db, job_id, store)
