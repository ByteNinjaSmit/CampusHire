import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, Timestamps, UUIDPk


def _rating_checks(*cols: str) -> tuple[CheckConstraint, ...]:
    return tuple(CheckConstraint(f"{c} BETWEEN 1 AND 5", name=c) for c in cols)


def _smallint_not_null() -> Mapped[int]:
    return mapped_column(SmallInteger, nullable=False)


class StudentFeedback(UUIDPk, Timestamps, Base):
    """Post-internship feedback: student rates company / internship."""

    __tablename__ = "student_feedback"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, unique=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.user_id"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    internship_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("internships.id"), nullable=False)
    company_culture: Mapped[int] = _smallint_not_null()
    mentorship: Mapped[int] = _smallint_not_null()
    technical_learning: Mapped[int] = _smallint_not_null()
    work_environment: Mapped[int] = _smallint_not_null()
    overall: Mapped[int] = _smallint_not_null()
    comments: Mapped[str | None] = mapped_column(Text)
    suggestions: Mapped[str | None] = mapped_column(Text)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    response_body: Mapped[str | None] = mapped_column(Text)
    responded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    application = relationship("Application", lazy="raise")
    student = relationship("Student", lazy="raise")
    company = relationship("Company", lazy="raise")
    internship = relationship("Internship", lazy="raise")
    responder = relationship("User", foreign_keys=[responded_by], lazy="raise")

    __table_args__ = (
        *_rating_checks("company_culture", "mentorship", "technical_learning", "work_environment", "overall"),
        Index("ix_student_feedback_company_id_created_at", "company_id", "created_at"),
        Index("ix_student_feedback_internship_id", "internship_id"),
    )


class CompanyFeedback(UUIDPk, Timestamps, Base):
    """Company / staff rates a student."""

    __tablename__ = "company_feedback"

    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    technical_skills: Mapped[int] = _smallint_not_null()
    soft_skills: Mapped[int] = _smallint_not_null()
    punctuality: Mapped[int] = _smallint_not_null()
    responsibility: Mapped[int] = _smallint_not_null()
    teamwork: Mapped[int] = _smallint_not_null()
    learning_ability: Mapped[int] = _smallint_not_null()
    strengths: Mapped[str | None] = mapped_column(Text)
    improvements: Mapped[str | None] = mapped_column(Text)
    hire_likelihood: Mapped[int] = _smallint_not_null()

    application = relationship("Application", lazy="raise")
    author = relationship("User", foreign_keys=[author_id], lazy="raise")

    __table_args__ = (
        UniqueConstraint("application_id", "author_id", name="uq_company_feedback_application_author"),
        *_rating_checks(
            "technical_skills", "soft_skills", "punctuality", "responsibility", "teamwork", "learning_ability",
            "hire_likelihood",
        ),
        Index("ix_company_feedback_application_id", "application_id"),
    )


class FacultyFeedback(UUIDPk, Timestamps, Base):
    __tablename__ = "faculty_feedback"

    internship_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("internships.id"), nullable=False)
    application_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("applications.id"))
    faculty_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_suitability: Mapped[int] = _smallint_not_null()
    learning_outcomes: Mapped[int] = _smallint_not_null()
    internship_quality: Mapped[int] = _smallint_not_null()
    suggestions: Mapped[str | None] = mapped_column(Text)
    comments: Mapped[str | None] = mapped_column(Text)

    internship = relationship("Internship", lazy="raise")
    application = relationship("Application", lazy="raise")
    faculty = relationship("User", foreign_keys=[faculty_id], lazy="raise")

    __table_args__ = (
        *_rating_checks("course_suitability", "learning_outcomes", "internship_quality"),
        Index("ix_faculty_feedback_internship_id", "internship_id"),
    )


class SystemFeedback(UUIDPk, Timestamps, Base):
    __tablename__ = "system_feedback"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(12), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    page_url: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="NEW", server_default=text("'NEW'"))
    priority: Mapped[str | None] = mapped_column(String(8))
    admin_notes: Mapped[str | None] = mapped_column(Text)

    user = relationship("User", foreign_keys=[user_id], lazy="raise")
    action_items = relationship(
        "FeedbackActionItem", back_populates="feedback", lazy="raise", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("type IN ('FEATURE','BUG','IMPROVEMENT')", name="type"),
        CheckConstraint("severity IS NULL OR severity IN ('LOW','MEDIUM','HIGH','CRITICAL')", name="severity"),
        CheckConstraint(
            "status IN ('NEW','TRIAGED','PLANNED','IN_PROGRESS','DONE','WONT_DO')", name="status"
        ),
        CheckConstraint("priority IS NULL OR priority IN ('LOW','MEDIUM','HIGH')", name="priority"),
        Index("ix_system_feedback_user_id", "user_id"),
        Index("ix_system_feedback_status", "status"),
    )


class FeedbackActionItem(UUIDPk, Timestamps, Base):
    __tablename__ = "feedback_action_items"

    system_feedback_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("system_feedback.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="OPEN", server_default=text("'OPEN'"))
    due_date: Mapped[date | None] = mapped_column(Date)

    feedback = relationship("SystemFeedback", back_populates="action_items", lazy="raise")
    assignee = relationship("User", foreign_keys=[assignee_id], lazy="raise")

    __table_args__ = (
        CheckConstraint("status IN ('OPEN','IN_PROGRESS','DONE')", name="status"),
        Index("ix_feedback_action_items_system_feedback_id", "system_feedback_id"),
    )
