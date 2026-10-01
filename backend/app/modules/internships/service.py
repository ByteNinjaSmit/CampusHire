"""Internship business rules (plan 3.5, 4.4)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import utcnow
from app.core.errors import AppError, conflict, forbidden, not_found, unprocessable
from app.core.pagination import PageParams, make_page
from app.core.permissions import can_manage_internship, member_company_id
from app.core.side_effects import audit, notify, queue_email
from app.modules.applications.models import Application
from app.modules.companies.models import Company
from app.modules.internships import repository as repo
from app.modules.internships import schemas as s
from app.modules.internships.models import Internship, SavedInternship
from app.modules.students.models import Student
from app.modules.users.models import User

CORE_FIELDS = {"title", "description", "start_date", "end_date", "application_deadline", "stipend_monthly", "duration_weeks"}
DATE_FIELDS = {"start_date", "end_date", "application_deadline"}


# ---- helpers ---------------------------------------------------------------------------------------
def _aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def _snapshot(i: Internship) -> dict[str, Any]:
    return {"status": i.status, "title": i.title, "archived": i.archived_at is not None}


def validate_dates(
    start: date, end: date, deadline: datetime, duration_weeks: int | None, *, check_future: bool
) -> int:
    """Return the effective duration_weeks. Raises 422 VALIDATION_ERROR with one detail per broken rule."""
    errors: list[dict[str, str]] = []
    today = datetime.now(UTC).date()
    if start >= end:
        errors.append({"field": "end_date", "message": "end_date must be after start_date"})
    days = (end - start).days
    if start < end and not 28 <= days <= 183:
        errors.append({"field": "end_date", "message": "Duration must be between 4 weeks and 6 months"})
    if deadline >= datetime.combine(start, time.min, tzinfo=UTC):
        errors.append({"field": "application_deadline", "message": "application_deadline must be before start_date"})
    if check_future:
        if start <= today:
            errors.append({"field": "start_date", "message": "start_date must be in the future"})
        if end <= today:
            errors.append({"field": "end_date", "message": "end_date must be in the future"})
        if deadline <= utcnow():
            errors.append({"field": "application_deadline", "message": "application_deadline must be in the future"})
    computed = round(days / 7) if days > 0 else 0
    if duration_weeks is not None and abs(duration_weeks - computed) > 1:
        errors.append(
            {"field": "duration_weeks", "message": f"duration_weeks must match the dates (about {computed} weeks)"}
        )
    if errors:
        raise unprocessable("Invalid internship dates", details=errors)
    return duration_weeks if duration_weeks is not None else computed


async def get_or_404(session: AsyncSession, internship_id: uuid.UUID, *, for_update: bool = False) -> Internship:
    i = await repo.get(session, internship_id, for_update=for_update)
    if i is None:
        raise not_found("Internship not found")
    return i


async def get_managed(
    session: AsyncSession, user: User, internship_id: uuid.UUID, *, for_update: bool = False
) -> Internship:
    """Internship the user may manage (owner/ADMIN); 404 otherwise (also hides existence)."""
    i = await get_or_404(session, internship_id, for_update=for_update)
    if not await can_manage_internship(session, user, i):
        raise not_found("Internship not found")
    return i


async def _logo_url(logo: tuple[str, str, str] | None) -> str | None:
    if not logo:
        return None
    from app.core import storage as storage_mod

    bucket, key, filename = logo
    try:
        return await storage_mod.get_storage().presign_get(bucket, key, filename)
    except Exception:  # noqa: BLE001 - never fail a listing because of a logo
        return None


async def to_summaries(session: AsyncSession, user: User, rows: list[Internship]) -> list[s.InternshipSummary]:
    ids = [r.id for r in rows]
    companies = await repo.company_map(session, {r.company_id for r in rows})
    saved = await repo.saved_ids(session, user.id, ids) if user.role == "STUDENT" else set()
    counts: dict[uuid.UUID, int] = {}
    if user.role != "STUDENT":
        counts = await repo.application_counts(session, ids)
    out: list[s.InternshipSummary] = []
    logo_cache: dict[uuid.UUID, str | None] = {}
    for r in rows:
        c = companies[r.company_id]
        if r.company_id not in logo_cache:
            logo_cache[r.company_id] = await _logo_url(c["logo"])
        out.append(
            s.InternshipSummary(
                id=r.id,
                title=r.title,
                domain=r.domain,
                location=r.location,
                work_mode=r.work_mode,  # type: ignore[arg-type]  # validated into the WorkMode enum
                stipend_monthly=r.stipend_monthly,
                currency=r.currency,
                duration_weeks=r.duration_weeks,
                start_date=r.start_date,
                end_date=r.end_date,
                application_deadline=r.application_deadline,
                status=r.status,
                skills=list(r.skills or []),
                company=s.CompanyRef(
                    id=c["id"], name=c["name"], logo_url=logo_cache[r.company_id], avg_rating=c["avg_rating"]
                ),
                is_saved=r.id in saved,
                application_count=counts.get(r.id, 0) if user.role != "STUDENT" else None,
                archived_at=r.archived_at,
                created_at=r.created_at,
            )
        )
    return out


async def to_detail(session: AsyncSession, user: User, i: Internship) -> s.Internship:
    summary = (await to_summaries(session, user, [i]))[0]
    poster = (await session.execute(select(User).where(User.id == i.posted_by))).scalar_one()
    manage = await can_manage_internship(session, user, i)
    my_app = None
    if user.role == "STUDENT":
        row = (
            await session.execute(
                select(Application.id, Application.status).where(
                    Application.internship_id == i.id, Application.student_id == user.id
                )
            )
        ).first()
        if row:
            my_app = s.MyApplication(id=row[0], status=row[1])
    is_open = i.status == "APPROVED" and i.archived_at is None and i.application_deadline > utcnow()
    return s.Internship(
        **summary.model_dump(),
        description=i.description,
        openings=i.openings,
        min_gpa=i.min_gpa,
        eligible_departments=list(i.eligible_departments or []),
        posted_by=s.PostedBy(id=poster.id, full_name=poster.full_name, role=poster.role),  # type: ignore[arg-type]
        rejection_reason=i.rejection_reason if manage else None,
        approved_at=i.approved_at,
        my_application=my_app,
        can_edit=manage and i.status != "CLOSED" and i.archived_at is None,
        can_apply=user.role == "STUDENT" and is_open and my_app is None,
    )


# ---- queries -----------------------------------------------------------------------------------------
async def list_internships(
    session: AsyncSession, user: User, f: repo.SearchFilters, params: PageParams
) -> dict[str, Any]:
    rows, total = await repo.search(session, user, f, params)
    return make_page(await to_summaries(session, user, rows), total, params)


async def facets(session: AsyncSession, user: User, f: repo.SearchFilters) -> dict[str, Any]:
    return await repo.facets(session, user, f)


async def get_detail(session: AsyncSession, user: User, internship_id: uuid.UUID) -> s.Internship:
    i = await get_or_404(session, internship_id)
    if user.role != "ADMIN" and not await can_manage_internship(session, user, i):
        visible = i.status == "APPROVED" and i.archived_at is None
        if not visible and user.role == "STUDENT":
            applied = (
                await session.execute(
                    select(Application.id).where(Application.internship_id == i.id, Application.student_id == user.id)
                )
            ).first()
            visible = applied is not None
        if not visible:
            raise not_found("Internship not found")
    return await to_detail(session, user, i)


async def saved(session: AsyncSession, user: User, params: PageParams) -> dict[str, Any]:
    rows, total = await repo.saved_list(session, user.id, params)
    return make_page(await to_summaries(session, user, rows), total, params)


async def recommended(session: AsyncSession, user: User, limit: int) -> list[s.InternshipSummary]:
    student = (await session.execute(select(Student).where(Student.user_id == user.id))).scalar_one_or_none()
    if student is None:
        return []
    applied = select(Application.internship_id).where(Application.student_id == user.id)
    stmt = (
        select(Internship)
        .where(repo.open_clause(), Internship.id.not_in(applied))
        .order_by(Internship.application_deadline)
        .limit(300)
    )
    cands = (await session.execute(stmt)).scalars().all()
    skills = {x.lower() for x in (student.skills or [])}
    dept = student.department.strip().lower()
    scored: list[tuple[float, Internship]] = []
    for c in cands:
        if c.min_gpa is not None and student.gpa < c.min_gpa:
            continue
        depts = {d.strip().lower() for d in (c.eligible_departments or [])}
        if depts and dept not in depts:
            continue
        overlap = len(skills & {x.lower() for x in (c.skills or [])})
        scored.append((overlap, c))
    scored.sort(key=lambda t: (-t[0], t[1].application_deadline))
    return await to_summaries(session, user, [c for _, c in scored[:limit]])


async def similar(session: AsyncSession, user: User, internship_id: uuid.UUID, limit: int) -> list[s.InternshipSummary]:
    base = await get_or_404(session, internship_id)
    if user.role != "ADMIN" and not await can_manage_internship(session, user, base):
        if not (base.status == "APPROVED" and base.archived_at is None):
            raise not_found("Internship not found")
    stmt = select(Internship).where(repo.open_clause(), Internship.id != base.id).limit(300)
    cands = (await session.execute(stmt.order_by(Internship.application_deadline))).scalars().all()
    skills = {x.lower() for x in (base.skills or [])}
    scored: list[tuple[float, Internship]] = []
    for c in cands:
        score = len(skills & {x.lower() for x in (c.skills or [])})
        if c.domain == base.domain:
            score += 3
        if c.company_id == base.company_id:
            score += 1
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda t: (-t[0], t[1].application_deadline))
    return await to_summaries(session, user, [c for _, c in scored[:limit]])


# ---- commands ----------------------------------------------------------------------------------------------
async def create(session: AsyncSession, user: User, data: s.InternshipCreateRequest) -> Internship:
    company = (await session.execute(select(Company).where(Company.id == data.company_id))).scalar_one_or_none()
    if company is None:
        raise unprocessable("Company not found", details=[{"field": "company_id", "message": "Unknown company"}])
    if user.role == "COMPANY":
        if await member_company_id(session, user) != company.id:
            raise forbidden("You can only post internships for your own company")
        if company.status != "ACTIVE":
            raise forbidden("Your company must be approved by an administrator before posting internships")
    elif company.status != "ACTIVE" and user.role != "ADMIN":
        raise unprocessable(
            "Company must be ACTIVE", details=[{"field": "company_id", "message": "Company is not active"}]
        )
    deadline = _aware(data.application_deadline)
    weeks = validate_dates(data.start_date, data.end_date, deadline, data.duration_weeks, check_future=True)
    now = utcnow()
    if user.role == "ADMIN":
        approved = data.submit is None or data.submit
        status = "APPROVED" if approved else "DRAFT"
    else:
        status = "PENDING_APPROVAL" if data.submit else "DRAFT"
    i = Internship(
        id=uuid.uuid4(),
        company_id=company.id,
        posted_by=user.id,
        title=data.title,
        description=data.description,
        domain=data.domain,
        location=data.location,
        work_mode=data.work_mode.value,
        stipend_monthly=data.stipend_monthly,
        currency=data.currency,
        duration_weeks=weeks,
        start_date=data.start_date,
        end_date=data.end_date,
        application_deadline=deadline,
        openings=data.openings,
        skills=data.skills,
        min_gpa=data.min_gpa,
        eligible_departments=data.eligible_departments,
        status=status,
    )
    if status == "APPROVED":
        i.approved_by = user.id
        i.approved_at = now
    session.add(i)
    await session.flush()
    audit(session, user, "internship.create", "internship", i.id, after={**_snapshot(i)})
    if status == "PENDING_APPROVAL":
        await _notify_admins_submitted(session, i, user)
    return i


async def _notify_admins_submitted(session: AsyncSession, i: Internship, actor: User) -> None:
    for admin in await repo.admin_users(session):
        if admin.id == actor.id:
            continue
        notify(
            session,
            admin.id,
            "INTERNSHIP_SUBMITTED",
            "Internship awaiting approval",
            f"{actor.full_name} submitted '{i.title}' for approval",
            "/admin/internships",
            {"internship_id": str(i.id)},
        )


async def update(session: AsyncSession, user: User, internship_id: uuid.UUID, data: s.InternshipUpdateRequest) -> Internship:
    i = await get_managed(session, user, internship_id, for_update=True)
    if i.status == "CLOSED" or i.archived_at is not None:
        raise conflict("Closed or archived internships cannot be edited", code="CONFLICT")
    changes = data.model_dump(exclude_unset=True)
    before = _snapshot(i)
    if not changes:
        return i
    start = changes.get("start_date", i.start_date)
    end = changes.get("end_date", i.end_date)
    deadline = _aware(changes["application_deadline"]) if "application_deadline" in changes else i.application_deadline
    dates_changed = bool(DATE_FIELDS & changes.keys())
    weeks_in = changes.get("duration_weeks")
    if "duration_weeks" not in changes and dates_changed:
        weeks_in = None  # recompute when dates change and no explicit value is given
    elif "duration_weeks" not in changes:
        weeks_in = i.duration_weeks
    weeks = validate_dates(start, end, deadline, weeks_in, check_future=dates_changed)
    for k, v in changes.items():
        if k in DATE_FIELDS or k == "duration_weeks":
            continue
        if k == "work_mode":
            v = v.value if hasattr(v, "value") else v
        setattr(i, k, v)
    i.start_date, i.end_date, i.application_deadline, i.duration_weeks = start, end, deadline, weeks
    resubmit = False
    if user.role != "ADMIN" and i.status == "APPROVED" and CORE_FIELDS & changes.keys():
        i.status = "PENDING_APPROVAL"
        i.approved_at = None
        i.approved_by = None
        resubmit = True
    await session.flush()
    audit(session, user, "internship.update", "internship", i.id, before=before, after={**_snapshot(i), "fields": sorted(changes)})
    if resubmit:
        await _notify_admins_submitted(session, i, user)
    return i


async def submit(session: AsyncSession, user: User, internship_id: uuid.UUID) -> Internship:
    i = await get_managed(session, user, internship_id, for_update=True)
    if i.status not in ("DRAFT", "REJECTED"):
        raise conflict(f"Cannot submit an internship in status {i.status}", code="INVALID_STATUS_TRANSITION")
    if i.archived_at is not None:
        raise conflict("Archived internships cannot be submitted", code="CONFLICT")
    validate_dates(i.start_date, i.end_date, i.application_deadline, i.duration_weeks, check_future=True)
    before = _snapshot(i)
    i.status = "PENDING_APPROVAL"
    i.rejection_reason = None
    await session.flush()
    audit(session, user, "internship.submit", "internship", i.id, before=before, after=_snapshot(i))
    await _notify_admins_submitted(session, i, user)
    return i


async def approve(session: AsyncSession, admin: User, internship_id: uuid.UUID) -> Internship:
    i = await get_or_404(session, internship_id, for_update=True)
    if i.status != "PENDING_APPROVAL":
        raise conflict(f"Cannot approve an internship in status {i.status}", code="INVALID_STATUS_TRANSITION")
    before = _snapshot(i)
    i.status = "APPROVED"
    i.rejection_reason = None
    i.approved_by = admin.id
    i.approved_at = utcnow()
    await session.flush()
    audit(session, admin, "internship.approve", "internship", i.id, before=before, after=_snapshot(i))
    await _notify_decision(session, i, approved=True)
    return i


async def reject(session: AsyncSession, admin: User, internship_id: uuid.UUID, reason: str) -> Internship:
    i = await get_or_404(session, internship_id, for_update=True)
    if i.status != "PENDING_APPROVAL":
        raise conflict(f"Cannot reject an internship in status {i.status}", code="INVALID_STATUS_TRANSITION")
    before = _snapshot(i)
    i.status = "REJECTED"
    i.rejection_reason = reason
    await session.flush()
    audit(session, admin, "internship.reject", "internship", i.id, before=before, after={**_snapshot(i), "reason": reason})
    await _notify_decision(session, i, approved=False)
    return i


async def _notify_decision(session: AsyncSession, i: Internship, *, approved: bool) -> None:
    poster = (await session.execute(select(User).where(User.id == i.posted_by))).scalar_one()
    link = ("/company" if poster.role == "COMPANY" else "/faculty") + "/internships"
    if poster.role == "ADMIN":
        link = "/admin/internships"
    data = {"internship_id": str(i.id), "status": i.status}
    if approved:
        notify(session, poster.id, "INTERNSHIP_APPROVED", "Internship approved", f"'{i.title}' is now live", link, data)
        queue_email(
            session,
            "internship_approved",
            poster.email,
            {"poster_name": poster.full_name, "internship_title": i.title, "link": link},
        )
    else:
        reason = i.rejection_reason or ""
        notify(
            session, poster.id, "INTERNSHIP_REJECTED", "Internship rejected", f"'{i.title}' was rejected: {reason}", link, data
        )
        queue_email(
            session,
            "internship_rejected",
            poster.email,
            {"poster_name": poster.full_name, "internship_title": i.title, "reason": reason, "link": link},
        )


async def close(session: AsyncSession, user: User, internship_id: uuid.UUID) -> Internship:
    i = await get_managed(session, user, internship_id, for_update=True)
    if i.status != "APPROVED":
        raise conflict(f"Cannot close an internship in status {i.status}", code="INVALID_STATUS_TRANSITION")
    before = _snapshot(i)
    i.status = "CLOSED"
    await session.flush()
    audit(session, user, "internship.close", "internship", i.id, before=before, after=_snapshot(i))
    return i


async def archive(session: AsyncSession, user: User, internship_id: uuid.UUID) -> Internship:
    i = await get_managed(session, user, internship_id, for_update=True)
    if i.archived_at is None:
        before = _snapshot(i)
        i.archived_at = utcnow()
        await session.flush()
        audit(session, user, "internship.archive", "internship", i.id, before=before, after=_snapshot(i))
    return i


async def restore(session: AsyncSession, admin: User, internship_id: uuid.UUID) -> Internship:
    i = await get_or_404(session, internship_id, for_update=True)
    if i.archived_at is not None:
        before = _snapshot(i)
        i.archived_at = None
        await session.flush()
        audit(session, admin, "internship.restore", "internship", i.id, before=before, after=_snapshot(i))
    return i


async def delete(session: AsyncSession, admin: User, internship_id: uuid.UUID) -> None:
    i = await get_or_404(session, internship_id, for_update=True)
    if await repo.application_total(session, i.id) > 0:
        raise conflict("This internship has applications and cannot be deleted; archive it instead", code="IN_USE")
    before = _snapshot(i)
    await session.execute(sa_delete(SavedInternship).where(SavedInternship.internship_id == i.id))
    await session.delete(i)
    await session.flush()
    audit(session, admin, "internship.delete", "internship", internship_id, before=before)


async def bulk(session: AsyncSession, admin: User, data: s.BulkInternshipAction) -> dict[str, Any]:
    if data.action == "reject" and not data.reason:
        raise unprocessable("A reason is required to reject", details=[{"field": "reason", "message": "Required"}])
    updated: list[uuid.UUID] = []
    failed: list[dict[str, Any]] = []
    for iid in dict.fromkeys(data.ids):
        try:
            async with session.begin_nested():
                if data.action == "approve":
                    await approve(session, admin, iid)
                elif data.action == "reject":
                    await reject(session, admin, iid, data.reason or "")
                elif data.action == "archive":
                    await archive(session, admin, iid)
                else:
                    await close(session, admin, iid)
            updated.append(iid)
        except AppError as exc:
            failed.append({"id": iid, "code": exc.code, "message": exc.message})
    return {"updated": updated, "failed": failed}


async def save(session: AsyncSession, user: User, internship_id: uuid.UUID) -> None:
    i = await get_or_404(session, internship_id)
    if not (i.status == "APPROVED" and i.archived_at is None):
        raise not_found("Internship not found")
    await session.execute(
        pg_insert(SavedInternship)
        .values(student_id=user.id, internship_id=i.id, created_at=utcnow())
        .on_conflict_do_nothing()
    )


async def unsave(session: AsyncSession, user: User, internship_id: uuid.UUID) -> None:
    await session.execute(
        sa_delete(SavedInternship).where(
            SavedInternship.student_id == user.id, SavedInternship.internship_id == internship_id
        )
    )


async def list_applications(
    session: AsyncSession, user: User, internship_id: uuid.UUID, statuses: list[str], q: str | None, params: PageParams
) -> dict[str, Any]:
    await get_managed(session, user, internship_id)
    from app.modules.applications import service as app_service

    return await app_service.list_applications(
        session, user, params, statuses=statuses, internship_id=internship_id, q=q
    )

