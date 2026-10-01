import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, CreatedAt, SoftArchive, Timestamps, UUIDPk

SEARCH_VECTOR_SQL = (
    "setweight(to_tsvector('english'::regconfig, coalesce(title,'')), 'A') || "
    "setweight(to_tsvector('english'::regconfig, coalesce(domain,'')), 'B') || "
    "setweight(to_tsvector('english'::regconfig, coalesce(location,'')), 'C') || "
    "setweight(to_tsvector('english'::regconfig, coalesce(description,'')), 'D')"
)


class Internship(UUIDPk, Timestamps, SoftArchive, Base):
    __tablename__ = "internships"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    posted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(60), nullable=False)
    location: Mapped[str] = mapped_column(String(160), nullable=False)
    work_mode: Mapped[str] = mapped_column(String(10), nullable=False)
    stipend_monthly: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0, server_default=text("0")
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR", server_default=text("'INR'"))
    duration_weeks: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    application_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    openings: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default=text("1"))
    skills: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list, server_default=text("'{}'"))
    min_gpa: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    eligible_departments: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=text("'{}'")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", server_default=text("'DRAFT'"))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    search_vector = mapped_column(TSVECTOR, Computed(SEARCH_VECTOR_SQL, persisted=True), deferred=True)

    company = relationship("Company", back_populates="internships", lazy="raise")
    poster = relationship("User", foreign_keys=[posted_by], lazy="raise")
    approver = relationship("User", foreign_keys=[approved_by], lazy="raise")

    __table_args__ = (
        CheckConstraint("length(title) >= 3", name="title"),
        CheckConstraint("length(description) >= 20", name="description"),
        CheckConstraint("work_mode IN ('ONSITE','REMOTE','HYBRID')", name="work_mode"),
        CheckConstraint("stipend_monthly >= 0", name="stipend"),
        CheckConstraint("duration_weeks BETWEEN 4 AND 26", name="duration_weeks"),
        CheckConstraint("openings > 0", name="openings"),
        CheckConstraint("min_gpa IS NULL OR (min_gpa >= 0 AND min_gpa <= 4)", name="min_gpa"),
        CheckConstraint(
            "status IN ('DRAFT','PENDING_APPROVAL','APPROVED','REJECTED','CLOSED')", name="status"
        ),
        CheckConstraint("start_date < end_date", name="dates"),
        CheckConstraint("(end_date - start_date) BETWEEN 28 AND 183", name="duration_days"),
        CheckConstraint("application_deadline < start_date::timestamptz", name="deadline_before_start"),
        Index("ix_internships_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "ix_internships_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
        Index("ix_internships_company_id", "company_id"),
        Index("ix_internships_posted_by", "posted_by"),
        Index("ix_internships_domain", "domain"),
        Index("ix_internships_stipend_monthly", "stipend_monthly"),
        Index("ix_internships_status_application_deadline", "status", "application_deadline"),
        Index(
            "ix_internships_open",
            "application_deadline",
            postgresql_where=text("status = 'APPROVED' AND archived_at IS NULL"),
        ),
    )


class SavedInternship(CreatedAt, Base):
    """[EXT] Student bookmarks."""

    __tablename__ = "saved_internships"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.user_id", ondelete="CASCADE"), primary_key=True
    )
    internship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("internships.id", ondelete="CASCADE"), primary_key=True
    )

