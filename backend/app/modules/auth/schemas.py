"""Auth schemas (plan section 6.2)."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.core.types import Gpa
from app.core.validators import normalize_registration_number
from app.modules.users.schemas import (
    Department,
    Email,
    FullName,
    Me,
    Password,
    Phone,
    Url,
)

__all__ = [
    "MessageResponse",
    "StudentRegisterRequest",
    "CompanyRegisterRequest",
    "CompanyRegisterInfo",
    "LoginRequest",
    "TokenResponse",
    "VerifyEmailRequest",
    "EmailRequest",
    "ResetPasswordRequest",
    "ChangePasswordRequest",
]


class MessageResponse(BaseModel):
    message: str


class StudentRegisterRequest(BaseModel):
    email: Email
    password: Password
    full_name: FullName
    phone: Phone
    department: Department
    gpa: Gpa
    enrollment_no: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)] | None = None
    graduation_year: Annotated[int, Field(ge=2000, le=2100)] | None = None


class CompanyRegisterInfo(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=160)]
    registration_number: str
    location: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=160)]
    industry: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = None
    website: Url | None = None
    contact_person_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
    contact_email: Email
    contact_phone: Phone | None = None

    @field_validator("registration_number")
    @classmethod
    def _reg_no(cls, v: str) -> str:
        return normalize_registration_number(v)


class CompanyRegisterRequest(BaseModel):
    email: Email
    password: Password
    full_name: FullName
    phone: Phone | None = None
    job_title: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = None
    company: CompanyRegisterInfo


class LoginRequest(BaseModel):
    # No password-policy / strict email validation on login: unknown credentials must give a generic 401.
    email: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=3, max_length=254)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=256)]


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: Me


class VerifyEmailRequest(BaseModel):
    token: Annotated[str, StringConstraints(min_length=10, max_length=200)]


class EmailRequest(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=3, max_length=254)]


class ResetPasswordRequest(BaseModel):
    token: Annotated[str, StringConstraints(min_length=10, max_length=200)]
    new_password: Password


class ChangePasswordRequest(BaseModel):
    current_password: Annotated[str, StringConstraints(min_length=1, max_length=256)]
    new_password: Password
