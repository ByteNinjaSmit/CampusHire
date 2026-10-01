"""Admin data access: audit logs, jobs, compliance policies / violations, login stats, worker sessions."""

import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.modules.admin.models import (
    AuditLog,
    CompliancePolicy,
    Job,
    LoginEvent,
    PolicyViolation,
)
from app.modules.applications.models import Application
from app.modules.documents.models import Document
from app.modules.users.models import User

SessionFactory = Callable[[], Any]  # () -> async context manager yielding an AsyncSession


# ---- sessions for workers / background jobs -------------------------------------------------------------
@asynccontextmanager
async def worker_session(session_factory: SessionFactory | None = None) -> AsyncIterator[AsyncSession]:
    """Own session for Celery-run job functions (NullPool engine; never reuses the API engine)."""
    if session_factory is not None:
        async with session_factory() as session:
            yield session
        return
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)() as session:
            yield session
    finally:
        await engine.dispose()


# ---- jobs --------------------------------------------------------------------------------------------------
async def get_job(session: AsyncSession, job_id: uuid.UUID) -> Job | None:
    return (await session.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()


def jobs_query(types: list[str], type_: str | None, status: str | None) -> Select[Any]:
    stmt = select(Job).where(Job.type.in_(types))
    if type_:
        stmt = stmt.where(Job.type == type_)
    if status:
        stmt = stmt.where(Job.status == status)
    return stmt.order_by(Job.created_at.desc(), Job.id)


async def get_document(session: AsyncSession, doc_id: uuid.UUID) -> Document | None:
    return (await session.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()


# ---- audit logs -------------------------------------------------------------------------------------------
def audit_query(
    actor_id: uuid.UUID | None,
    entity_type: str | None,
    action: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> Select[Any]:
    stmt = select(AuditLog, User).outerjoin(User, User.id == AuditLog.actor_id)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if action:
        stmt = stmt.where(AuditLog.action.startswith(action, autoescape=True))
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.created_at <= date_to)
    return stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())


# ---- compliance ---------------------------------------------------------------------------------------------
async def list_policies(session: AsyncSession) -> list[tuple[CompliancePolicy, int]]:
    open_count = (
        select(func.count())
        .select_from(PolicyViolation)
        .where(PolicyViolation.policy_id == CompliancePolicy.id, PolicyViolation.status == "OPEN")
        .scalar_subquery()
    )
    rows = await session.execute(select(CompliancePolicy, open_count).order_by(CompliancePolicy.code))
    return [(p, int(n)) for p, n in rows.all()]


async def get_policy(session: AsyncSession, policy_id: uuid.UUID) -> CompliancePolicy | None:
    return (
        await session.execute(select(CompliancePolicy).where(CompliancePolicy.id == policy_id))
    ).scalar_one_or_none()


async def get_policy_by_code(session: AsyncSession, code: str) -> CompliancePolicy | None:
    return (await session.execute(select(CompliancePolicy).where(CompliancePolicy.code == code))).scalar_one_or_none()


async def open_violation_count(session: AsyncSession, policy_id: uuid.UUID) -> int:
    return int(
        (
            await session.execute(
                select(func.count())
                .select_from(PolicyViolation)
                .where(PolicyViolation.policy_id == policy_id, PolicyViolation.status == "OPEN")
            )
        ).scalar_one()
    )


def violations_query(status: str | None, policy_code: str | None) -> Select[Any]:
    resolver = User.__table__.alias("resolver")
    stmt = (
        select(PolicyViolation, CompliancePolicy, resolver.c.id, resolver.c.full_name, resolver.c.role)
        .join(CompliancePolicy, CompliancePolicy.id == PolicyViolation.policy_id)
        .outerjoin(resolver, resolver.c.id == PolicyViolation.resolved_by)
    )
    if status:
        stmt = stmt.where(PolicyViolation.status == status)
    if policy_code:
        stmt = stmt.where(CompliancePolicy.code == policy_code)
    return stmt.order_by(PolicyViolation.created_at.desc(), PolicyViolation.id)


async def get_violation(session: AsyncSession, violation_id: uuid.UUID) -> PolicyViolation | None:
    return (
        await session.execute(select(PolicyViolation).where(PolicyViolation.id == violation_id))
    ).scalar_one_or_none()


def document_queue_query(verification_status: str, kind: str | None) -> Select[Any]:
    active_apps = (
        select(func.count())
        .select_from(Application)
        .where(
            Application.resume_document_id == Document.id,
            Application.status.notin_(("REJECTED", "WITHDRAWN")),
        )
        .scalar_subquery()
    )
    stmt = (
        select(Document, User, active_apps)
        .join(User, User.id == Document.owner_id)
        .where(
            Document.status == "UPLOADED",
            Document.deleted_at.is_(None),
            Document.verification_status == verification_status,
            Document.kind.notin_(("EXPORT", "REPORT", "IMPORT")),
        )
    )
    if kind:
        stmt = stmt.where(Document.kind == kind)
    return stmt.order_by(Document.created_at.asc(), Document.id)


# ---- login stats ----------------------------------------------------------------------------------------------
async def login_trend(session: AsyncSession, since: datetime) -> list[tuple[Any, int, int]]:
    day = func.date_trunc("day", LoginEvent.created_at)
    rows = await session.execute(
        select(
            day,
            func.count().filter(LoginEvent.success.is_(True)),
            func.count().filter(LoginEvent.success.is_(False)),
        )
        .where(LoginEvent.created_at >= since)
        .group_by(day)
        .order_by(day)
    )
    return [(d, int(s), int(f)) for d, s, f in rows.all()]


async def logins_since(session: AsyncSession, since: datetime) -> int:
    return int(
        (
            await session.execute(
                select(func.count())
                .select_from(LoginEvent)
                .where(LoginEvent.created_at >= since, LoginEvent.success.is_(True))
            )
        ).scalar_one()
    )


async def active_users_since(session: AsyncSession, since: datetime) -> int:
    return int(
        (
            await session.execute(
                select(func.count(func.distinct(LoginEvent.user_id))).where(
                    LoginEvent.created_at >= since, LoginEvent.success.is_(True), LoginEvent.user_id.is_not(None)
                )
            )
        ).scalar_one()
    )
