"""Student schemas (plan 6.3, 6.5)."""

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.core.types import ApplicationStatus, Gpa
from app.modules.users.schemas import (
    Department,
    DocumentSummary,
    FullName,
    Phone,
    StudentProfile,
    Url,
)

Skill = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
Bio = Annotated[str, StringConstraints(max_length=2000)]


class StudentProfileUpdate(BaseModel):
    """PATCH /students/me. Every field optional; explicit null clears nullable fields."""

    phone: Phone | None = None
    department: Department | None = None
    gpa: Gpa | None = None
    graduation_year: Annotated[int, Field(ge=2000, le=2100)] | None = None
    skills: Annotated[list[Skill], Field(max_length=50)] | None = None
    bio: Bio | None = None
    linkedin_url: Url | None = None
    github_url: Url | None = None
    portfolio_url: Url | None = None

    @field_validator("linkedin_url", "github_url", "portfolio_url", "bio", mode="before")
    @classmethod
    def _blank_to_none(cls, v: object) -> object:
        return None if isinstance(v, str) and not v.strip() else v

    @field_validator("skills")
    @classmethod
    def _dedupe_skills(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        seen: dict[str, str] = {}
        for item in v:
            seen.setdefault(item.lower(), item)
        return list(seen.values())


class AdminStudentUpdate(StudentProfileUpdate):
    """PATCH /students/{id} (ADMIN): also name and enrollment number."""

    full_name: FullName | None = None
    enrollment_no: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)] | None = None


class ResumeSelect(BaseModel):
    document_id: uuid.UUID


class DeactivateIn(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class StudentStats(BaseModel):
    total_applications: int = 0
    by_status: dict[ApplicationStatus, int]
    interviews_upcoming: int = 0


class StudentListItem(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: str
    phone: str | None = None
    department: str
    gpa: Gpa
    is_active: bool
    application_count: int
    placed: bool


class StudentDetail(StudentListItem):
    profile: StudentProfile
    stats: StudentStats


class StudentMe(StudentProfile):
    """GET/PATCH /students/me: the profile (plan 6.3) plus identity fields and stats."""

    full_name: str
    email: str
    phone: str | None = None
    stats: StudentStats


class AppInternshipRef(BaseModel):
    id: uuid.UUID
    title: str
    company_id: uuid.UUID
    company_name: str
    company_logo_url: str | None = None
    application_deadline: datetime
    start_date: date


class AppStudentRef(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    department: str
    gpa: Gpa


class ApplicationSummary(BaseModel):
    """Plan 6.5 ApplicationSummary (history rows under /students/{id}/applications)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ApplicationStatus
    status_changed_at: datetime
    created_at: datetime
    internship: AppInternshipRef
    student: AppStudentRef
    next_interview_at: datetime | None = None
    evaluation_avg: float | None = None


__all__ = [
    "AdminStudentUpdate",
    "ApplicationSummary",
    "DeactivateIn",
    "DocumentSummary",
    "ResumeSelect",
    "StudentDetail",
    "StudentListItem",
    "StudentMe",
    "StudentProfile",
    "StudentProfileUpdate",
    "StudentStats",
]

