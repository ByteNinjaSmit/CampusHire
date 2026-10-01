"""Feedback schemas (plan 6.8). Ratings are strict integers 1-5."""

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.types import Role

Rating = Annotated[int, Field(strict=True, ge=1, le=5)]

SystemType = Literal["FEATURE", "BUG", "IMPROVEMENT"]
Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
SystemStatus = Literal["NEW", "TRIAGED", "PLANNED", "IN_PROGRESS", "DONE", "WONT_DO"]
Priority = Literal["LOW", "MEDIUM", "HIGH"]
ActionStatus = Literal["OPEN", "IN_PROGRESS", "DONE"]

DIMENSIONS = ("overall", "company_culture", "mentorship", "technical_learning", "work_environment")


class Ref(BaseModel):
    id: uuid.UUID
    full_name: str


class CompanyRef(BaseModel):
    id: uuid.UUID
    name: str


class InternshipRef(BaseModel):
    id: uuid.UUID
    title: str


# ---- student feedback ---------------------------------------------------------------------------------
class StudentFeedbackCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    application_id: uuid.UUID
    company_culture: Rating
    mentorship: Rating
    technical_learning: Rating
    work_environment: Rating
    overall: Rating
    comments: str | None = Field(default=None, max_length=5000)
    suggestions: str | None = Field(default=None, max_length=5000)
    is_anonymous: bool = False


class StudentFeedback(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    company_culture: int
    mentorship: int
    technical_learning: int
    work_environment: int
    overall: int
    comments: str | None = None
    suggestions: str | None = None
    is_anonymous: bool
    student_name: str | None = None
    company: CompanyRef
    internship: InternshipRef
    response_body: str | None = None
    responded_by_name: str | None = None
    responded_at: datetime | None = None
    created_at: datetime


class FeedbackResponseRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    body: str = Field(min_length=1, max_length=3000)


class FeedbackTrendSeries(BaseModel):
    dimension: Literal["overall", "company_culture", "mentorship", "technical_learning", "work_environment"]
    values: list[float | None]


class FeedbackTrends(BaseModel):
    months: list[str]
    series: list[FeedbackTrendSeries]
    counts: list[int]


class RatingSummary(BaseModel):
    """Aggregated company rating (plan 6.3); shared with the companies module."""

    count: int
    overall: float | None = None
    company_culture: float | None = None
    mentorship: float | None = None
    technical_learning: float | None = None
    work_environment: float | None = None
    distribution: dict[str, int]


# ---- company feedback ---------------------------------------------------------------------------------
class CompanyFeedbackCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    application_id: uuid.UUID
    technical_skills: Rating
    soft_skills: Rating
    punctuality: Rating
    responsibility: Rating
    teamwork: Rating
    learning_ability: Rating
    strengths: str | None = Field(default=None, max_length=5000)
    improvements: str | None = Field(default=None, max_length=5000)
    hire_likelihood: Rating


class CompanyFeedback(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    technical_skills: int
    soft_skills: int
    punctuality: int
    responsibility: int
    teamwork: int
    learning_ability: int
    strengths: str | None = None
    improvements: str | None = None
    hire_likelihood: int
    author_name: str
    student: Ref
    internship: InternshipRef
    average: float
    created_at: datetime


# ---- faculty feedback ---------------------------------------------------------------------------------
class FacultyFeedbackCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    internship_id: uuid.UUID
    application_id: uuid.UUID | None = None
    course_suitability: Rating
    learning_outcomes: Rating
    internship_quality: Rating
    suggestions: str | None = Field(default=None, max_length=5000)
    comments: str | None = Field(default=None, max_length=5000)


class FacultyFeedback(BaseModel):
    id: uuid.UUID
    internship_id: uuid.UUID
    application_id: uuid.UUID | None = None
    course_suitability: int
    learning_outcomes: int
    internship_quality: int
    suggestions: str | None = None
    comments: str | None = None
    faculty_name: str
    internship_title: str
    created_at: datetime


# ---- system feedback ----------------------------------------------------------------------------------
class SystemFeedbackCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    type: SystemType
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=5, max_length=5000)
    page_url: str | None = Field(default=None, max_length=1000)
    severity: Severity | None = None


class SystemFeedbackUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: SystemStatus | None = None
    priority: Priority | None = None
    admin_notes: str | None = Field(default=None, max_length=5000)


class ActionItemCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=160)
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None


class ActionItemUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: ActionStatus | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    due_date: date | None = None
    assignee_id: uuid.UUID | None = None


class ActionItem(BaseModel):
    id: uuid.UUID
    title: str
    assignee: Ref | None = None
    status: ActionStatus
    due_date: date | None = None
    created_at: datetime


class SystemFeedbackUser(BaseModel):
    id: uuid.UUID
    full_name: str
    role: Role


class SystemFeedback(BaseModel):
    id: uuid.UUID
    type: SystemType
    title: str
    description: str
    page_url: str | None = None
    severity: Severity | None = None
    user: SystemFeedbackUser
    status: SystemStatus
    priority: Priority | None = None
    admin_notes: str | None = None
    action_items: list[ActionItem]
    created_at: datetime


class DayCount(BaseModel):
    date: date
    count: int


class SystemFeedbackSummary(BaseModel):
    by_type: dict[str, int]
    by_status: dict[str, int]
    last_30_days: list[DayCount]
    open_action_items: int
