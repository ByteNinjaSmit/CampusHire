import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, Timestamps


class Student(Timestamps, Base):
    __tablename__ = "students"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    enrollment_no: Mapped[str | None] = mapped_column(String(32), unique=True)
    department: Mapped[str] = mapped_column(String(80), nullable=False)
    gpa: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    graduation_year: Mapped[int | None] = mapped_column(SmallInteger)
    skills: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=text("'{}'")
    )
    bio: Mapped[str | None] = mapped_column(Text)
    linkedin_url: Mapped[str | None] = mapped_column(Text)
    github_url: Mapped[str | None] = mapped_column(Text)
    portfolio_url: Mapped[str | None] = mapped_column(Text)
    default_resume_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )

    user = relationship("User", back_populates="student", lazy="raise")
    default_resume = relationship("Document", foreign_keys=[default_resume_id], lazy="raise")

    __table_args__ = (
        CheckConstraint("gpa >= 0.0 AND gpa <= 4.0", name="gpa"),
        CheckConstraint("graduation_year IS NULL OR graduation_year BETWEEN 2000 AND 2100", name="graduation_year"),
        CheckConstraint("bio IS NULL OR length(bio) <= 2000", name="bio"),
        Index("ix_students_department", "department"),
        Index("ix_students_gpa", "gpa"),
    )
