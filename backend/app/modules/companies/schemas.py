"""Company schemas (plan 6.3, 6.4 summary rows, and the ratings / members shapes in types-extra.ts)."""

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, StringConstraints, field_validator

from app.core.types import CompanyStatus, Money, WorkMode
from app.core.validators import normalize_registration_number
from app.modules.users.schemas import Email, Phone, Url

RegistrationNumber = Annotated[str, AfterValidator(normalize_registration_number)]
Name160 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=160)]
Location = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
ContactName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
Industry = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]

_OPTIONAL_TEXT = ("industry", "website", "description", "contact_phone")


class CompanyCreateRequest(BaseModel):
    name: Name160
    registration_number: RegistrationNumber
    location: Location
    industry: Industry | None = None
    website: Url | None = None
    description: Description | None = None
    contact_person_name: ContactName
    contact_email: Email
    contact_phone: Phone | None = None
    logo_document_id: uuid.UUID | None = None

    @field_validator(*_OPTIONAL_TEXT, mode="before")
    @classmethod
    def _blank_to_none(cls, v: object) -> object:
        return None if isinstance(v, str) and not v.strip() else v


class CompanyUpdateRequest(BaseModel):
    """PATCH: every field optional. Explicit null clears nullable fields."""

    name: Name160 | None = None
    registration_number: RegistrationNumber | None = None
    location: Location | None = None
    industry: Industry | None = None
    website: Url | None = None
    description: Description | None = None
    contact_person_name: ContactName | None = None
    contact_email: Email | None = None
    contact_phone: Phone | None = None
    logo_document_id: uuid.UUID | None = None

    @field_validator(*_OPTIONAL_TEXT, mode="before")
    @classmethod
    def _blank_to_none(cls, v: object) -> object:
        return None if isinstance(v, str) and not v.strip() else v


class RatingSummary(BaseModel):
    count: int = 0
    overall: float | None = None
    company_culture: float | None = None
    mentorship: float | None = None
    technical_learning: float | None = None
    work_environment: float | None = None
    distribution: dict[str, int] = Field(default_factory=lambda: {str(i): 0 for i in range(1, 6)})


class CompanySummary(BaseModel):
    id: uuid.UUID
    name: str
    registration_number: str
    industry: str | None = None
    location: str
    logo_url: str | None = None
    status: CompanyStatus
    avg_rating: float | None = None
    rating_count: int = 0
    open_internships: int = 0


class Company(CompanySummary):
    website: str | None = None
    description: str | None = None
    contact_person_name: str
    contact_email: str
    contact_phone: str | None = None
    archived_at: datetime | None = None
    created_at: datetime
    rating_summary: RatingSummary
    internship_count: int = 0  # all internships of the company (hard delete is blocked while > 0)


class CompanyMember(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: str
    job_title: str | None = None


class RecentRating(BaseModel):
    id: uuid.UUID
    overall: int
    comments: str | None = None
    student_name: str | None = None  # null when the student chose anonymity (ADMIN still sees it)
    internship_title: str
    created_at: datetime


class CompanyRatingsResponse(BaseModel):
    summary: RatingSummary
    recent: list[RecentRating]


class CompanyRef(BaseModel):
    id: uuid.UUID
    name: str
    logo_url: str | None = None
    avg_rating: float | None = None


class CompanyInternshipItem(BaseModel):
    """Same shape as plan 6.4 InternshipSummary."""

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
