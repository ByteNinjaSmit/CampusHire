"""Interview schemas (plan 6.6)."""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.types import InterviewMode, InterviewResult, InterviewStatus
from app.core.validators import validate_email


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class StudentRef(BaseModel):
    id: uuid.UUID
    full_name: str


class InterviewInternshipRef(BaseModel):
    id: uuid.UUID
    title: str
    company_name: str


class Interview(BaseModel):
    """``comments`` is internal: it is left unset (omitted from the JSON) for STUDENT viewers."""

    id: uuid.UUID
    application_id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int
    mode: InterviewMode
    location: str | None = None
    meeting_link: str | None = None
    interviewer_name: str
    interviewer_email: str | None = None
    status: InterviewStatus
    result: InterviewResult
    score: int | None = None
    comments: str | None = None
    feedback_for_student: str | None = None
    cancel_reason: str | None = None
    reschedule_count: int
    student: StudentRef
    internship: InterviewInternshipRef
    created_at: datetime


class InterviewCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    application_id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=15, le=240)
    mode: InterviewMode
    location: str | None = Field(default=None, max_length=500)
    meeting_link: str | None = Field(default=None, max_length=1000)
    interviewer_name: str = Field(min_length=1, max_length=120)
    interviewer_email: str | None = None
    interviewer_user_id: uuid.UUID | None = None

    @field_validator("scheduled_at")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return _as_utc(v)

    @field_validator("interviewer_email")
    @classmethod
    def _email(cls, v: str | None) -> str | None:
        return validate_email(v) if v else None

    @field_validator("location", "meeting_link")
    @classmethod
    def _blank_to_none(cls, v: str | None) -> str | None:
        return v or None

    @model_validator(mode="after")
    def _mode_requirements(self) -> "InterviewCreateRequest":
        # R5: ONLINE needs a meeting link, ONSITE needs a location
        if self.mode == InterviewMode.ONLINE and not self.meeting_link:
            raise ValueError("meeting_link is required for ONLINE interviews")
        if self.mode == InterviewMode.ONSITE and not self.location:
            raise ValueError("location is required for ONSITE interviews")
        return self


class InterviewRescheduleRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    scheduled_at: datetime
    duration_minutes: int | None = Field(default=None, ge=15, le=240)
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("scheduled_at")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return _as_utc(v)


class InterviewResultRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: InterviewStatus
    result: InterviewResult
    score: int | None = Field(default=None, ge=1, le=5)
    comments: str | None = Field(default=None, max_length=5000)
    feedback_for_student: str | None = Field(default=None, max_length=5000)

    @field_validator("status")
    @classmethod
    def _status(cls, v: InterviewStatus) -> InterviewStatus:
        if v not in (InterviewStatus.COMPLETED, InterviewStatus.NO_SHOW):
            raise ValueError("status must be COMPLETED or NO_SHOW")
        return v


class InterviewCancelRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    reason: str = Field(min_length=1, max_length=1000)
