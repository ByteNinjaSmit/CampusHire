import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, Timestamps, UUIDPk


class Interview(UUIDPk, Timestamps, Base):
    __tablename__ = "interviews"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=30, server_default=text("30")
    )
    mode: Mapped[str] = mapped_column(String(10), nullable=False)
    location: Mapped[str | None] = mapped_column(Text)
    meeting_link: Mapped[str | None] = mapped_column(Text)
    interviewer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    interviewer_email: Mapped[str | None] = mapped_column(CITEXT)
    interviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(
        String(12), nullable=False, default="SCHEDULED", server_default=text("'SCHEDULED'")
    )
    result: Mapped[str] = mapped_column(String(10), nullable=False, default="PENDING", server_default=text("'PENDING'"))
    score: Mapped[int | None] = mapped_column(SmallInteger)
    comments: Mapped[str | None] = mapped_column(Text)
    feedback_for_student: Mapped[str | None] = mapped_column(Text)
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    reschedule_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default=text("0"))
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    application = relationship("Application", back_populates="interviews", lazy="raise")
    scheduler = relationship("User", foreign_keys=[scheduled_by], lazy="raise")
    interviewer = relationship("User", foreign_keys=[interviewer_user_id], lazy="raise")

    __table_args__ = (
        CheckConstraint("duration_minutes BETWEEN 15 AND 240", name="duration_minutes"),
        CheckConstraint("mode IN ('ONLINE','ONSITE','PHONE')", name="mode"),
        CheckConstraint(
            "status IN ('SCHEDULED','RESCHEDULED','COMPLETED','CANCELLED','NO_SHOW')", name="status"
        ),
        CheckConstraint("result IN ('PENDING','PASS','FAIL','ON_HOLD')", name="result"),
        CheckConstraint("score IS NULL OR score BETWEEN 1 AND 5", name="score"),
        Index("ix_interviews_application_id", "application_id"),
        Index("ix_interviews_scheduled_at", "scheduled_at"),
        Index("ix_interviews_interviewer_user_id_scheduled_at", "interviewer_user_id", "scheduled_at"),
    )
