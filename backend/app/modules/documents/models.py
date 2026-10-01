import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, Timestamps, UUIDPk


class Document(UUIDPk, Timestamps, Base):
    """[EXT] Documents center; also backs the spec's mandatory-resume rule."""

    __tablename__ = "documents"

    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    bucket: Mapped[str] = mapped_column(String(32), nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PENDING_UPLOAD", server_default=text("'PENDING_UPLOAD'")
    )
    verification_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PENDING", server_default=text("'PENDING'")
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_note: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner = relationship("User", foreign_keys=[owner_id], lazy="raise")
    verifier = relationship("User", foreign_keys=[verified_by], lazy="raise")

    __table_args__ = (
        CheckConstraint(
            "kind IN ('RESUME','COVER_LETTER','TRANSCRIPT','OFFER_LETTER','LOGO','REPORT','EXPORT','IMPORT','OTHER')",
            name="kind",
        ),
        CheckConstraint("bucket IN ('resumes','documents','reports')", name="bucket"),
        CheckConstraint("size_bytes > 0", name="size_bytes"),
        CheckConstraint("status IN ('PENDING_UPLOAD','UPLOADED','REJECTED')", name="status"),
        CheckConstraint("verification_status IN ('PENDING','VERIFIED','REJECTED')", name="verification_status"),
        CheckConstraint(
            "kind <> 'RESUME' OR (content_type = 'application/pdf' AND size_bytes <= 5242880)",
            name="resume_pdf",
        ),
        Index("ix_documents_owner_id_kind", "owner_id", "kind"),
    )
