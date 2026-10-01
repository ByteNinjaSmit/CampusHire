import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, SoftArchive, Timestamps, UUIDPk
from app.modules.users.models import PHONE_RE

# Indian CIN (21 chars) or international "CC-XXXXXX" (ISO country code, hyphen, 6-15 alphanumerics)
REG_NO_RE = r"^([LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}|[A-Z]{2}-[A-Z0-9]{6,15})$"


class Company(UUIDPk, Timestamps, SoftArchive, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    industry: Mapped[str | None] = mapped_column(String(80))
    location: Mapped[str] = mapped_column(String(160), nullable=False)
    website: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    logo_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    contact_person_name: Mapped[str] = mapped_column(String(120), nullable=False)
    contact_email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ACTIVE", server_default=text("'ACTIVE'")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    members = relationship("CompanyMember", back_populates="company", lazy="raise")
    internships = relationship("Internship", back_populates="company", lazy="raise")

    __table_args__ = (
        CheckConstraint(f"registration_number ~ '{REG_NO_RE}'", name="registration_number"),
        CheckConstraint(f"contact_phone IS NULL OR contact_phone ~ '{PHONE_RE}'", name="contact_phone"),
        CheckConstraint("status IN ('PENDING','ACTIVE','ARCHIVED')", name="status"),
        Index(
            "ix_companies_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index("ix_companies_status", "status"),
    )


class CompanyMember(Timestamps, Base):
    """[EXT] COMPANY role: links a company user to its company."""

    __tablename__ = "company_members"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    job_title: Mapped[str | None] = mapped_column(String(80))

    user = relationship("User", back_populates="company_member", lazy="raise")
    company = relationship("Company", back_populates="members", lazy="raise")

    __table_args__ = (Index("ix_company_members_company_id", "company_id"),)
