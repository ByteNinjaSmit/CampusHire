"""Application schemas (plan section 6.5; Interview / Evaluation shapes from 6.6 / 6.7)."""

import uuid
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.core.types import ApplicationStatus, Gpa, Money
from app.modules.users.schemas import DocumentSummary

Status = ApplicationStatus
Text = Annotated[str, StringConstraints(strip_whitespace=True)]


# ---- requests ---------------------------------------------------------------------------------------
class ApplicationAnswers(BaseModel):
    skills: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]] | None = Field(
        default=None, max_length=30
    )
    coursework: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None
    availability_from: date | None = None
    portfolio_url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500, pattern=r"^https?://\S+$")] | None = None


class ApplicationCreateRequest(BaseModel):
    internship_id: uuid.UUID
    # Optional at the schema level so that a missing resume yields the dedicated 422 RESUME_REQUIRED.
    resume_document_id: uuid.UUID | None = None
    cover_letter: Annotated[str, StringConstraints(strip_whitespace=True, min_length=50, max_length=5000)]
    qualifications: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=3000)]
    answers: ApplicationAnswers | None = None


class OfferDetails(BaseModel):
    stipend_monthly: Annotated[Money, Field(ge=0, max_digits=10, decimal_places=2)]
    start_date: date
    joining_location: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    notes: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None


class ApplicationStatusUpdateRequest(BaseModel):
    status: Status
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None
    offer_details: OfferDetails | None = None


class BulkStatusRequest(BaseModel):
    ids: Annotated[list[uuid.UUID], Field(min_length=1, max_length=200)]
    status: Status
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None


class WithdrawRequest(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None


# ---- responses --------------------------------------------------------------------------------------
class ApplicationInternshipRef(BaseModel):
    id: uuid.UUID
    title: str
    company_id: uuid.UUID
    company_name: str
    company_logo_url: str | None = None
    application_deadline: datetime
    start_date: date


class ApplicationStudentRef(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    department: str
    gpa: Gpa


class ApplicationSummary(BaseModel):
    id: uuid.UUID
    status: Status
    status_changed_at: datetime
    created_at: datetime
    internship: ApplicationInternshipRef
    student: ApplicationStudentRef
    next_interview_at: datetime | None = None
    evaluation_avg: float | None = None


class TimelineEvent(BaseModel):
    at: datetime
    kind: Literal[
        "STATUS",
        "INTERVIEW_SCHEDULED",
        "INTERVIEW_RESCHEDULED",
        "INTERVIEW_CANCELLED",
        "INTERVIEW_COMPLETED",
        "EVALUATION",
        "COMPLETED",
    ]
    status: Status | None = None
    title: str
    note: str | None = None
    actor_name: str | None = None


class PersonRef(BaseModel):
    id: uuid.UUID
    full_name: str


class InterviewInternshipRef(BaseModel):
    id: uuid.UUID
    title: str
    company_name: str


class InterviewOut(BaseModel):
    """Plan 6.6 ``Interview``. ``comments`` is only populated for non-student viewers (key omitted for students)."""

    id: uuid.UUID
    application_id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int
    mode: str
    location: str | None = None
    meeting_link: str | None = None
    interviewer_name: str
    interviewer_email: str | None = None
    status: str
    result: str
    score: int | None = None
    comments: str | None = None
    feedback_for_student: str | None = None
    cancel_reason: str | None = None
    reschedule_count: int
    student: PersonRef
    internship: InterviewInternshipRef
    created_at: datetime


class EvaluationSummaryOut(BaseModel):
    id: uuid.UUID
    form_name: str
    evaluator_name: str
    weighted_score: float
    recommendation: str
    created_at: datetime
    shared_with_student: bool


class ApplicationDetail(ApplicationSummary):
    cover_letter: str
    qualifications: str
    answers: dict[str, Any]
    resume: DocumentSummary
    decision_note: str | None = None
    offer_details: dict[str, Any] | None = None
    withdrawn_reason: str | None = None
    completed_at: datetime | None = None
    timeline: list[TimelineEvent]
    interviews: list[InterviewOut]
    evaluations: list[EvaluationSummaryOut]
    allowed_transitions: list[Status]
    can_give_student_feedback: bool = False
    student_feedback_id: uuid.UUID | None = None
    company_feedback_ids: list[uuid.UUID] = []


class BulkStatusFailure(BaseModel):
    id: uuid.UUID
    code: str
    message: str | None = None


class BulkStatusResult(BaseModel):
    updated: list[uuid.UUID]
    failed: list[BulkStatusFailure]


class ResumeUrl(BaseModel):
    url: str
    expires_in: int
