import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, CreatedAt, Timestamps, UUIDPk, utcnow


class Application(UUIDPk, Timestamps, Base):
    __tablename__ = "applications"

    internship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("internships.id", ondelete="RESTRICT"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.user_id"), nullable=False
    )
    resume_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    cover_letter: Mapped[str] = mapped_column(Text, nullable=False)
    qualifications: Mapped[str] = mapped_column(Text, nullable=False)
    answers: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING", server_default=text("'PENDING'"))
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    decision_note: Mapped[str | None] = mapped_column(Text)
    offer_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    withdrawn_reason: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    internship = relationship("Internship", lazy="raise")
    student = relationship("Student", lazy="raise")
    resume_document = relationship("Document", foreign_keys=[resume_document_id], lazy="raise")
    history = relationship(
        "ApplicationStatusHistory",
        back_populates="application",
        order_by="ApplicationStatusHistory.created_at",
        lazy="raise",
    )
    interviews = relationship("Interview", back_populates="application", lazy="raise")

    __table_args__ = (
        UniqueConstraint("student_id", "internship_id", name="uq_applications_student_internship"),
        CheckConstraint("length(cover_letter) BETWEEN 50 AND 5000", name="cover_letter"),
        CheckConstraint("length(qualifications) BETWEEN 10 AND 3000", name="qualifications"),
        CheckConstraint(
            "status IN ('PENDING','UNDER_REVIEW','SHORTLISTED','INTERVIEW','ACCEPTED','REJECTED','WITHDRAWN')",
            name="status",
        ),
        Index("ix_applications_internship_id_status", "internship_id", "status"),
        Index("ix_applications_student_id_status", "student_id", "status"),
        Index("ix_applications_status_changed_at", "status_changed_at"),
    )


class ApplicationStatusHistory(CreatedAt, Base):
    __tablename__ = "application_status_history"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(16))
    to_status: Mapped[str] = mapped_column(String(16), nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(Text)

    application = relationship("Application", back_populates="history", lazy="raise")

    __table_args__ = (Index("ix_application_status_history_application_id_created_at", "application_id", "created_at"),)
