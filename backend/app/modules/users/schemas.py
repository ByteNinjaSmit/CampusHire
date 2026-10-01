"""User schemas (plan section 6.2 / 6.3). Profile + document summary schemas are reused by auth and students."""

import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.core.types import Gpa, Role
from app.core.validators import normalize_phone, validate_email, validate_password

# ---- reusable annotated field types ----------------------------------------------------------------
Email = Annotated[str, AfterValidator(validate_email)]
Phone = Annotated[str, AfterValidator(normalize_phone)]
Password = Annotated[str, AfterValidator(validate_password)]
FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
Department = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
_URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)


def validate_url(v: str) -> str:
    v = v.strip()
    if not _URL_RE.match(v):
        raise ValueError("Must be a valid http(s) URL")
    return v


Url = Annotated[str, AfterValidator(validate_url)]


# ---- profiles -----------------------------------------------------------------------------------------
class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    filename: str
    content_type: str
    size_bytes: int
    status: str
    verification_status: str
    created_at: datetime


class StudentProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    department: str
    gpa: Gpa
    enrollment_no: str | None = None
    graduation_year: int | None = None
    skills: list[str] = []
    bio: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    default_resume: DocumentSummary | None = None


class FacultyProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    department: str
    designation: str | None = None
    employee_id: str | None = None


class CompanyMembership(BaseModel):
    company_id: uuid.UUID
    company_name: str
    company_status: str
    job_title: str | None = None


class Me(BaseModel):
    id: uuid.UUID
    email: str
    role: Role
    full_name: str
    phone: str | None = None
    avatar_url: str | None = None
    email_verified: bool
    is_active: bool
    created_at: datetime
    student: StudentProfile | None = None
    faculty: FacultyProfile | None = None
    company: CompanyMembership | None = None


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: Role
    full_name: str
    phone: str | None = None
    is_active: bool
    email_verified: bool
    last_login_at: datetime | None = None
    created_at: datetime


class UserDetail(UserSummary):
    avatar_url: str | None = None
    deactivated_at: datetime | None = None
    deactivated_reason: str | None = None
    student: StudentProfile | None = None
    faculty: FacultyProfile | None = None
    company: CompanyMembership | None = None


# ---- requests -----------------------------------------------------------------------------------------
class StudentCreate(BaseModel):
    department: Department
    gpa: Gpa
    enrollment_no: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)] | None = None
    graduation_year: Annotated[int, Field(ge=2000, le=2100)] | None = None


class FacultyCreate(BaseModel):
    department: Department
    designation: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = None
    employee_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)] | None = None


class CompanyLink(BaseModel):
    company_id: uuid.UUID
    job_title: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = None


class AdminCreateUserRequest(BaseModel):
    email: Email
    password: Password
    full_name: FullName
    role: Role
    phone: Phone | None = None
    mark_verified: bool = False
    student: StudentCreate | None = None
    faculty: FacultyCreate | None = None
    company: CompanyLink | None = None


class StudentProfileUpdateIn(BaseModel):
    """Partial update of the student profile (admin)."""

    department: Department | None = None
    gpa: Gpa | None = None
    enrollment_no: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)] | None = None
    graduation_year: Annotated[int, Field(ge=2000, le=2100)] | None = None
    skills: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]] | None = Field(
        default=None, max_length=50
    )
    bio: Annotated[str, StringConstraints(max_length=2000)] | None = None
    linkedin_url: Url | None = None
    github_url: Url | None = None
    portfolio_url: Url | None = None


class FacultyProfileUpdateIn(BaseModel):
    department: Department | None = None
    designation: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = None
    employee_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)] | None = None


class UpdateUserRequest(BaseModel):
    full_name: FullName | None = None
    phone: Phone | None = None
    student: StudentProfileUpdateIn | None = None
    faculty: FacultyProfileUpdateIn | None = None


class UpdateMeRequest(BaseModel):
    full_name: FullName | None = None
    phone: Phone | None = None
    avatar_url: Url | None = None

    @field_validator("avatar_url", mode="before")
    @classmethod
    def _empty_avatar_to_none(cls, v: object) -> object:
        return None if v == "" else v


class DeactivateRequest(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class BulkUserAction(BaseModel):
    ids: Annotated[list[uuid.UUID], Field(min_length=1, max_length=200)]
    action: Literal["deactivate", "activate"]
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None


class BulkFailure(BaseModel):
    id: uuid.UUID
    code: str
    message: str


class BulkActionResult(BaseModel):
    updated: list[uuid.UUID]
    failed: list[BulkFailure]

