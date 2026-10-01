"""Admin-owned tables: jobs, audit_logs, login_events, compliance_policies, policy_violations."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, CreatedAt, Timestamps, UUIDPk


class LoginEvent(CreatedAt, Base):
    __tablename__ = "login_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    email: Mapped[str | None] = mapped_column(CITEXT)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_login_events_created_at", "created_at"),)


class AuditLog(CreatedAt, Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)

    actor = relationship("User", foreign_keys=[actor_id], lazy="raise")

    __table_args__ = (
        Index("ix_audit_logs_entity_type_entity_id", "entity_type", "entity_id"),
        Index("ix_audit_logs_actor_id", "actor_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )


class Job(UUIDPk, Timestamps, Base):
    """Async exports, imports, reports and compliance scans."""

    __tablename__ = "jobs"

    type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="QUEUED", server_default=text("'QUEUED'"))
    requested_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    params: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    progress: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default=text("0"))
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"))
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    requester = relationship("User", foreign_keys=[requested_by], lazy="raise")

    __table_args__ = (
        CheckConstraint("type IN ('REPORT_EXPORT','DATA_EXPORT','DATA_IMPORT','COMPLIANCE_SCAN')", name="type"),
        CheckConstraint("status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED')", name="status"),
        CheckConstraint("progress BETWEEN 0 AND 100", name="progress"),
        Index("ix_jobs_requested_by", "requested_by"),
        Index("ix_jobs_type_status", "type", "status"),
    )


class CompliancePolicy(UUIDPk, Timestamps, Base):
    __tablename__ = "compliance_policies"

    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    severity: Mapped[str] = mapped_column(String(8), nullable=False, default="MEDIUM", server_default=text("'MEDIUM'"))


class PolicyViolation(UUIDPk, Timestamps, Base):
    __tablename__ = "policy_violations"

    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_policies.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="OPEN", server_default=text("'OPEN'"))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)

    policy = relationship("CompliancePolicy", lazy="raise")

    __table_args__ = (
        UniqueConstraint("policy_id", "entity_type", "entity_id", name="uq_policy_violations_policy_entity"),
        CheckConstraint("status IN ('OPEN','RESOLVED','DISMISSED')", name="status"),
        Index("ix_policy_violations_status", "status"),
    )
