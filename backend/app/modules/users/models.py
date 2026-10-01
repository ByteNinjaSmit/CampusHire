from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, Timestamps, UUIDPk

PHONE_RE = r"^\+?[1-9][0-9]{9,14}$"


class User(UUIDPk, Timestamps, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deactivated_reason: Mapped[str | None] = mapped_column(Text)

    student = relationship("Student", back_populates="user", uselist=False, lazy="raise")
    faculty = relationship("Faculty", back_populates="user", uselist=False, lazy="raise")
    company_member = relationship("CompanyMember", back_populates="user", uselist=False, lazy="raise")

    __table_args__ = (
        CheckConstraint(r"email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$'", name="email"),
        CheckConstraint("role IN ('ADMIN','FACULTY','STUDENT','COMPANY')", name="role"),
        CheckConstraint("length(trim(full_name)) >= 2", name="full_name"),
        CheckConstraint(f"phone IS NULL OR phone ~ '{PHONE_RE}'", name="phone"),
        Index("ix_users_role", "role"),
        Index(
            "ix_users_full_name_trgm",
            "full_name",
            postgresql_using="gin",
            postgresql_ops={"full_name": "gin_trgm_ops"},
        ),
    )

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None
