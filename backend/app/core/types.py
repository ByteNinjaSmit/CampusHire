"""Shared types: Decimal serializers and enums mirrored from the DB CHECK constraints."""

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import Field, PlainSerializer

# Pydantic v2 serialises Decimal as a string; the wire format must be a JSON number (plan 1.3).
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
Gpa = Annotated[
    Decimal,
    Field(ge=0, le=4, max_digits=3, decimal_places=2),
    PlainSerializer(float, return_type=float, when_used="json"),
]


class Role(StrEnum):
    ADMIN = "ADMIN"
    FACULTY = "FACULTY"
    STUDENT = "STUDENT"
    COMPANY = "COMPANY"


class ApplicationStatus(StrEnum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    SHORTLISTED = "SHORTLISTED"
    INTERVIEW = "INTERVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class InternshipStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class CompanyStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class WorkMode(StrEnum):
    ONSITE = "ONSITE"
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"


class InterviewStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    RESCHEDULED = "RESCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


class InterviewResult(StrEnum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"
    ON_HOLD = "ON_HOLD"


class InterviewMode(StrEnum):
    ONLINE = "ONLINE"
    ONSITE = "ONSITE"
    PHONE = "PHONE"


class DocumentKind(StrEnum):
    RESUME = "RESUME"
    COVER_LETTER = "COVER_LETTER"
    TRANSCRIPT = "TRANSCRIPT"
    OFFER_LETTER = "OFFER_LETTER"
    LOGO = "LOGO"
    REPORT = "REPORT"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    OTHER = "OTHER"


class DocumentStatus(StrEnum):
    PENDING_UPLOAD = "PENDING_UPLOAD"
    UPLOADED = "UPLOADED"
    REJECTED = "REJECTED"


class VerificationStatus(StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class JobType(StrEnum):
    REPORT_EXPORT = "REPORT_EXPORT"
    DATA_EXPORT = "DATA_EXPORT"
    DATA_IMPORT = "DATA_IMPORT"
    COMPLIANCE_SCAN = "COMPLIANCE_SCAN"


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


INTERNSHIP_DOMAINS = [
    "Software Engineering",
    "Data Science",
    "AI/ML",
    "Cloud & DevOps",
    "Cybersecurity",
    "Product Design",
    "Product Management",
    "Marketing",
    "Finance",
    "Operations",
    "Hardware/Embedded",
    "Research",
]

MAX_RESUME_BYTES = 5_242_880
