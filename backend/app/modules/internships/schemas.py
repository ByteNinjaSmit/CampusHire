"""Internship schemas (plan section 6.4)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.core.types import INTERNSHIP_DOMAINS, Gpa, Money, Role, WorkMode


def _clean_list(values: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    for v in values:
        v = " ".join(str(v).split())
        if not v:
            continue
        if len(v) > 60:
            raise ValueError("Each item must be at most 60 characters")
        seen.setdefault(v.lower(), v)
    if len(seen) > 30:
        raise ValueError("At most 30 items are allowed")
    return list(seen.values())


StrList = Annotated[list[str], AfterValidator(_clean_list)]
StipendIn = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
GpaIn = Annotated[Decimal, Field(ge=0, le=4, max_digits=3, decimal_places=2)]


def _domain(v: str) -> str:
    if v not in INTERNSHIP_DOMAINS:
        raise ValueError(f"Domain must be one of: {', '.join(INTERNSHIP_DOMAINS)}")
    return v


Domain = Annotated[str, AfterValidator(_domain)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=160)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=20, max_length=10000)]
Location = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=160)]
Currency = Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Z]{3}$")]


# ---- responses ------------------------------------------------------------------------------------
class CompanyRef(BaseModel):
    id: uuid.UUID
    name: str
    logo_url: str | None = None
    avg_rating: float | None = None


class InternshipSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    domain: str
    location: str
    work_mode: WorkMode
    stipend_monthly: Money
    currency: str
    duration_weeks: int
    start_date: date
    end_date: date
    application_deadline: datetime
    status: str
    skills: list[str]
    company: CompanyRef
    is_saved: bool = False
    application_count: int | None = None
    archived_at: datetime | None = None
    created_at: datetime


class PostedBy(BaseModel):
    id: uuid.UUID
    full_name: str
    role: Role


class MyApplication(BaseModel):
    id: uuid.UUID
    status: str


class Internship(InternshipSummary):
    description: str
    openings: int
    min_gpa: Gpa | None = None
    eligible_departments: list[str]
    posted_by: PostedBy
    rejection_reason: str | None = None
    approved_at: datetime | None = None
    my_application: MyApplication | None = None
    can_edit: bool = False
    can_apply: bool = False


class FacetValue(BaseModel):
    value: str
    count: int


class FacetCompany(BaseModel):
    id: uuid.UUID
    name: str
    count: int


class FacetStipend(BaseModel):
    min: float
    max: float


class InternshipFacets(BaseModel):
    domains: list[FacetValue]
    locations: list[FacetValue]
    companies: list[FacetCompany]
    work_modes: list[FacetValue]
    stipend: FacetStipend


class BulkFailure(BaseModel):
    id: uuid.UUID
    code: str
    message: str


class BulkActionResult(BaseModel):
    updated: list[uuid.UUID]
    failed: list[BulkFailure]


class SaveResult(BaseModel):
    is_saved: bool


# ---- requests ---------------------------------------------------------------------------------------
class InternshipCreateRequest(BaseModel):
    company_id: uuid.UUID
    title: Title
    description: Description
    domain: Domain
    location: Location
    work_mode: WorkMode
    stipend_monthly: StipendIn
    currency: Currency = "INR"
    duration_weeks: int | None = Field(default=None, ge=4, le=26)
    start_date: date
    end_date: date
    application_deadline: datetime
    openings: int = Field(default=1, ge=1, le=1000)
    skills: StrList = []
    min_gpa: GpaIn | None = None
    eligible_departments: StrList = []
    # Admin creates APPROVED directly when submit is true or omitted; everybody else: DRAFT unless submit=true.
    submit: bool | None = None


class InternshipUpdateRequest(BaseModel):
    """Partial update (every field optional). ``company_id`` / ``submit`` cannot be changed here."""

    title: Title | None = None
    description: Description | None = None
    domain: Domain | None = None
    location: Location | None = None
    work_mode: WorkMode | None = None
    stipend_monthly: StipendIn | None = None
    currency: Currency | None = None
    duration_weeks: int | None = Field(default=None, ge=4, le=26)
    start_date: date | None = None
    end_date: date | None = None
    application_deadline: datetime | None = None
    openings: int | None = Field(default=None, ge=1, le=1000)
    skills: StrList | None = None
    min_gpa: GpaIn | None = None
    eligible_departments: StrList | None = None

    @field_validator("title", "description", "domain", "location", "work_mode", "stipend_monthly", mode="before")
    @classmethod
    def _no_null(cls, v):  # NOT NULL columns cannot be cleared
        if v is None:
            raise ValueError("This field cannot be null")
        return v


class RejectRequest(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=2000)]


class BulkInternshipAction(BaseModel):
    ids: Annotated[list[uuid.UUID], Field(min_length=1, max_length=200)]
    action: Literal["approve", "reject", "archive", "close"]
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=2000)] | None = None
