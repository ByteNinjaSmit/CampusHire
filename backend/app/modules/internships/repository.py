"""Internship queries: scoped search (FTS + pg_trgm), facets, enrichment helpers."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, desc, func, literal_column, or_, select, text, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import utcnow
from app.core.pagination import PageParams
from app.core.permissions import member_company_id, owned_internships_clause
from app.modules.applications.models import Application
from app.modules.companies.models import Company
from app.modules.documents.models import Document
from app.modules.feedback.models import StudentFeedback
from app.modules.internships.models import Internship, SavedInternship
from app.modules.users.models import User

SORTS = ("relevance", "newest", "stipend_desc", "deadline_asc")


@dataclass
class SearchFilters:
    q: str | None = None
    domain: list[str] = field(default_factory=list)
    company_id: list[uuid.UUID] = field(default_factory=list)
    location: str | None = None
    work_mode: list[str] = field(default_factory=list)
    stipend_min: Decimal | None = None
    stipend_max: Decimal | None = None
    duration_min: int | None = None
    duration_max: int | None = None
    skills: list[str] = field(default_factory=list)
    deadline_before: datetime | None = None
    deadline_after: datetime | None = None
    status: list[str] = field(default_factory=list)
    mine: bool = False
    include_archived: bool = False
    sort: str = "relevance"


def open_clause() -> Any:
    """Internships a student may apply to / browse: APPROVED, not archived, deadline in the future."""
    return and_(
        Internship.status == "APPROVED", Internship.archived_at.is_(None), Internship.application_deadline > utcnow()
    )


def visible_for_detail_clause() -> Any:
    return and_(Internship.status == "APPROVED", Internship.archived_at.is_(None))


async def scope_clause(session: AsyncSession, user: User, f: SearchFilters) -> Any:
    """Row-level visibility for the list endpoint (plan 4.4)."""
    if user.role == "ADMIN":
        return true() if f.include_archived else Internship.archived_at.is_(None)
    if user.role in ("FACULTY", "COMPANY") and f.mine:
        company_id = await member_company_id(session, user)
        clause = owned_internships_clause(user, company_id)
        return clause if f.include_archived else and_(clause, Internship.archived_at.is_(None))
    return open_clause()


def filter_clauses(f: SearchFilters, user: User) -> list[Any]:
    conds: list[Any] = []
    if f.domain:
        conds.append(Internship.domain.in_(f.domain))
    if f.company_id:
        conds.append(Internship.company_id.in_(f.company_id))
    if f.location:
        conds.append(Internship.location.ilike(f"%{_escape_like(f.location)}%", escape="\\"))
    if f.work_mode:
        conds.append(Internship.work_mode.in_(f.work_mode))
    if f.stipend_min is not None:
        conds.append(Internship.stipend_monthly >= f.stipend_min)
    if f.stipend_max is not None:
        conds.append(Internship.stipend_monthly <= f.stipend_max)
    if f.duration_min is not None:
        conds.append(Internship.duration_weeks >= f.duration_min)
    if f.duration_max is not None:
        conds.append(Internship.duration_weeks <= f.duration_max)
    if f.skills:
        lowered = [s.lower() for s in f.skills]
        conds.append(
            func.lower(func.array_to_string(Internship.skills, literal_column("'|'"))).op("~")(
                "(^|\\|)(" + "|".join(_escape_re(s) for s in lowered) + ")(\\||$)"
            )
        )
    if f.deadline_before is not None:
        conds.append(Internship.application_deadline <= f.deadline_before)
    if f.deadline_after is not None:
        conds.append(Internship.application_deadline >= f.deadline_after)
    # status filter only means something where non-open rows are visible (ADMIN, or staff with mine=true)
    if f.status and (user.role == "ADMIN" or (user.role in ("FACULTY", "COMPANY") and f.mine)):
        conds.append(Internship.status.in_(f.status))
    return conds


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _escape_re(s: str) -> str:
    import re

    return re.escape(s).replace("\\ ", " ")


def _tsquery(q: str) -> Any:
    return func.websearch_to_tsquery(literal_column("'english'::regconfig"), q)


async def search(
    session: AsyncSession, user: User, f: SearchFilters, params: PageParams
) -> tuple[list[Internship], int]:
    conds = [await scope_clause(session, user, f), *filter_clauses(f, user)]
    base = select(Internship).join(Company, Company.id == Internship.company_id)
    order: list[Any]
    q = (f.q or "").strip()
    if q:
        await session.execute(text("SELECT set_config('pg_trgm.similarity_threshold', '0.25', true)"))
        tsq = _tsquery(q)
        conds.append(
            or_(
                Internship.search_vector.op("@@")(tsq),
                Internship.title.op("%")(q),
                Company.name.op("%")(q),
            )
        )
    sort = f.sort if f.sort in SORTS else "relevance"
    if sort == "relevance" and q:
        order = [
            desc(func.ts_rank(Internship.search_vector, _tsquery(q))),
            desc(func.similarity(Internship.title, q)),
            desc(Internship.created_at),
        ]
    elif sort == "stipend_desc":
        order = [desc(Internship.stipend_monthly), desc(Internship.created_at)]
    elif sort == "deadline_asc":
        order = [Internship.application_deadline.asc(), desc(Internship.created_at)]
    else:  # newest / relevance without q
        order = [desc(Internship.created_at), Internship.id]
    total = (
        await session.execute(
            select(func.count()).select_from(Internship).join(Company, Company.id == Internship.company_id).where(*conds)
        )
    ).scalar_one()
    rows = (
        (await session.execute(base.where(*conds).order_by(*order).offset(params.offset).limit(params.limit)))
        .scalars()
        .all()
    )
    return list(rows), int(total)


async def facets(session: AsyncSession, user: User, f: SearchFilters) -> dict[str, Any]:
    scope = await scope_clause(session, user, f)
    base = Internship.id.in_(select(Internship.id).where(scope))

    async def counts(col: Any, limit: int = 50) -> list[tuple[Any, int]]:
        res = await session.execute(
            select(col, func.count()).where(base).group_by(col).order_by(desc(func.count()), col).limit(limit)
        )
        return [(r[0], int(r[1])) for r in res.all()]

    domains = await counts(Internship.domain)
    locations = await counts(Internship.location)
    modes = await counts(Internship.work_mode)
    comp_rows = (
        await session.execute(
            select(Company.id, Company.name, func.count())
            .join(Internship, Internship.company_id == Company.id)
            .where(base)
            .group_by(Company.id, Company.name)
            .order_by(desc(func.count()), Company.name)
            .limit(50)
        )
    ).all()
    lo, hi = (
        await session.execute(select(func.min(Internship.stipend_monthly), func.max(Internship.stipend_monthly)).where(base))
    ).one()
    return {
        "domains": [{"value": v, "count": c} for v, c in domains],
        "locations": [{"value": v, "count": c} for v, c in locations],
        "companies": [{"id": r[0], "name": r[1], "count": int(r[2])} for r in comp_rows],
        "work_modes": [{"value": v, "count": c} for v, c in modes],
        "stipend": {"min": float(lo or 0), "max": float(hi or 0)},
    }


# ---- lookups -------------------------------------------------------------------------------------
async def get(session: AsyncSession, internship_id: uuid.UUID, *, for_update: bool = False) -> Internship | None:
    stmt = select(Internship).where(Internship.id == internship_id)
    if for_update:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    return (await session.execute(stmt)).scalar_one_or_none()


async def company_map(session: AsyncSession, company_ids: set[uuid.UUID]) -> dict[uuid.UUID, dict[str, Any]]:
    """company_id -> {id, name, logo (bucket, key, filename)|None, avg_rating}"""
    if not company_ids:
        return {}
    rows = (
        await session.execute(
            select(Company.id, Company.name, Document.bucket, Document.object_key, Document.filename)
            .outerjoin(Document, Document.id == Company.logo_document_id)
            .where(Company.id.in_(company_ids))
        )
    ).all()
    ratings = {
        r[0]: float(r[1])
        for r in (
            await session.execute(
                select(StudentFeedback.company_id, func.avg(StudentFeedback.overall))
                .where(StudentFeedback.company_id.in_(company_ids))
                .group_by(StudentFeedback.company_id)
            )
        ).all()
        if r[1] is not None
    }
    return {
        r[0]: {
            "id": r[0],
            "name": r[1],
            "logo": (r[2], r[3], r[4]) if r[2] else None,
            "avg_rating": round(ratings[r[0]], 2) if r[0] in ratings else None,
        }
        for r in rows
    }


async def saved_ids(session: AsyncSession, student_id: uuid.UUID, internship_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not internship_ids:
        return set()
    res = await session.execute(
        select(SavedInternship.internship_id).where(
            SavedInternship.student_id == student_id, SavedInternship.internship_id.in_(internship_ids)
        )
    )
    return set(res.scalars().all())


async def application_counts(session: AsyncSession, internship_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not internship_ids:
        return {}
    res = await session.execute(
        select(Application.internship_id, func.count())
        .where(Application.internship_id.in_(internship_ids))
        .group_by(Application.internship_id)
    )
    return {r[0]: int(r[1]) for r in res.all()}


async def saved_list(
    session: AsyncSession, student_id: uuid.UUID, params: PageParams
) -> tuple[list[Internship], int]:
    base = (
        select(Internship)
        .join(SavedInternship, SavedInternship.internship_id == Internship.id)
        .where(SavedInternship.student_id == student_id, Internship.archived_at.is_(None))
    )
    total = (
        await session.execute(
            select(func.count())
            .select_from(SavedInternship)
            .join(Internship, SavedInternship.internship_id == Internship.id)
            .where(SavedInternship.student_id == student_id, Internship.archived_at.is_(None))
        )
    ).scalar_one()
    rows = (
        await session.execute(
            base.order_by(desc(SavedInternship.created_at)).offset(params.offset).limit(params.limit)
        )
    ).scalars().all()
    return list(rows), int(total)


async def application_total(session: AsyncSession, internship_id: uuid.UUID) -> int:
    return int(
        (
            await session.execute(select(func.count()).select_from(Application).where(Application.internship_id == internship_id))
        ).scalar_one()
    )


async def admin_users(session: AsyncSession) -> list[User]:
    return list(
        (await session.execute(select(User).where(User.role == "ADMIN", User.is_active.is_(True)))).scalars().all()
    )
