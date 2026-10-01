"""Admin schemas. ``Job`` follows plan 6.9 exactly; the rest are admin-only shapes (documented in the WP4c report)."""

import uuid
from datetime import date as Date
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

from app.core.types import JobStatus, JobType, Role

ExportEntity = Literal["students", "companies", "internships", "applications", "feedback"]
ImportEntity = Literal["students", "companies"]
ExportFormat = Literal["csv", "xlsx"]


# ---- jobs (plan 6.9) ----------------------------------------------------------------------------------
class JobResultError(BaseModel):
    row: int
    field: str
    message: str


class JobResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    rows_ok: int | None = None
    rows_failed: int | None = None
    errors: list[JobResultError] | None = None


class Job(BaseModel):
    id: uuid.UUID
    type: JobType
    status: JobStatus
    progress: int
    params: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    download_url: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class JobDownload(BaseModel):
    url: str
    expires_in: int


def job_out(job: Any, download_url: str | None = None) -> Job:
    """Build the wire ``Job`` from a ``jobs`` row."""
    return Job(
        id=job.id,
        type=job.type,
        status=job.status,
        progress=job.progress,
        params=job.params or {},
        result=job.result,
        error=job.error,
        download_url=download_url,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


# ---- health -------------------------------------------------------------------------------------------
class ComponentHealth(BaseModel):
    status: Literal["ok", "down"]
    latency_ms: float | None = None
    detail: str | None = None


class BucketHealth(BaseModel):
    bucket: str
    status: Literal["ok", "down"]
    latency_ms: float | None = None
    object_count: int | None = None
    size_bytes: int | None = None
    truncated: bool = False
    detail: str | None = None


class MinioHealth(ComponentHealth):
    buckets: list[BucketHealth] = []
    total_size_bytes: int = 0


class CeleryHealth(ComponentHealth):
    workers: list[str] = []


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    checked_at: datetime
    db: ComponentHealth
    redis: ComponentHealth
    minio: MinioHealth
    celery: CeleryHealth
    queue_depth: int | None = None


# ---- metrics ------------------------------------------------------------------------------------------
class MetricPoint(BaseModel):
    minute: datetime
    requests: int
    errors: int
    p50_ms: float | None = None
    p95_ms: float | None = None


class MetricTotals(BaseModel):
    requests: int
    errors: int
    error_rate: float
    avg_ms: float | None = None
    p50_ms: float | None = None
    p95_ms: float | None = None


class LoginTrendPoint(BaseModel):
    date: Date
    success: int
    failed: int


class MetricsResponse(BaseModel):
    minutes: int
    points: list[MetricPoint]
    totals: MetricTotals
    login_trend: list[LoginTrendPoint]
    active_users_24h: int
    logins_last_hour: int


# ---- audit --------------------------------------------------------------------------------------------
class ActorRef(BaseModel):
    id: uuid.UUID
    full_name: str
    role: Role


class AuditLogOut(BaseModel):
    id: int
    actor: ActorRef | None = None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None = None
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    ip: str | None = None
    user_agent: str | None = None
    created_at: datetime


# ---- compliance ---------------------------------------------------------------------------------------
Severity = Literal["LOW", "MEDIUM", "HIGH"]


class PolicyOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    is_active: bool
    severity: str
    open_violations: int = 0
    created_at: datetime


class PolicyCreate(BaseModel):
    code: Annotated[
        str,
        BeforeValidator(lambda v: v.strip().upper() if isinstance(v, str) else v),
        StringConstraints(pattern=r"^[A-Z][A-Z0-9_]{2,39}$"),
    ]
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=160)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None
    severity: Severity = "MEDIUM"
    is_active: bool = True


class PolicyUpdate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=160)] | None = None
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None
    severity: Severity | None = None
    is_active: bool | None = None


class PolicyRef(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    severity: str


class ViolationOut(BaseModel):
    id: uuid.UUID
    policy: PolicyRef
    entity_type: str
    entity_id: uuid.UUID
    details: dict[str, Any]
    status: Literal["OPEN", "RESOLVED", "DISMISSED"]
    resolved_by: ActorRef | None = None
    resolved_at: datetime | None = None
    note: str | None = None
    created_at: datetime


class ViolationUpdate(BaseModel):
    status: Literal["OPEN", "RESOLVED", "DISMISSED"]
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None


class OwnerRef(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str


class DocumentQueueItem(BaseModel):
    id: uuid.UUID
    kind: str
    filename: str
    content_type: str
    size_bytes: int
    status: str
    verification_status: str
    owner: OwnerRef
    active_applications: int
    created_at: datetime


# ---- export / import ----------------------------------------------------------------------------------
class ExportRequest(BaseModel):
    entity: ExportEntity
    format: ExportFormat = "csv"
    filters: dict[str, Any] = Field(default_factory=dict)
