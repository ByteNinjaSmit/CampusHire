"""Company management (spec section 4 + [EXT] COMPANY role approval flow)."""

import uuid
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import utcnow
from app.core.errors import AppError, conflict, forbidden, not_found, unprocessable
from app.core.pagination import PageParams, make_page, paginate
from app.core.permissions import member_company_id
from app.core.side_effects import audit, notify
from app.core.storage import Storage
from app.modules.companies import repository as repo
from app.modules.companies import schemas as s
from app.modules.companies.models import Company as CompanyModel
from app.modules.users.models import User

EMPTY_RATING = s.RatingSummary()


# ---- builders ------------------------------------------------------------------------------------------------
async def logo_url_map(
    session: AsyncSession, storage: Storage, document_ids: list[uuid.UUID | None]
) -> dict[uuid.UUID, str]:
    """document_id -> presigned GET url for UPLOADED, non-deleted logo documents."""
    ids = [d for d in dict.fromkeys(document_ids) if d is not None]
    docs = await repo.logo_documents(session, ids)
    return {did: await storage.presign_get(d.bucket, d.object_key, d.filename) for did, d in docs.items()}


async def summaries(
    session: AsyncSession, storage: Storage, companies: list[CompanyModel]
) -> list[s.CompanySummary]:
    ids = [c.id for c in companies]
    ratings = await repo.rating_summaries(session, ids)
    opens = await repo.open_counts(session, ids)
    logos = await logo_url_map(session, storage, [c.logo_document_id for c in companies])
    out = []
    for c in companies:
        r = ratings.get(c.id)
        out.append(
            s.CompanySummary(
                id=c.id,
                name=c.name,
                registration_number=c.registration_number,
                industry=c.industry,
                location=c.location,
                logo_url=logos.get(c.logo_document_id) if c.logo_document_id else None,
                status=c.status,  # type: ignore[arg-type]  # validated into the CompanyStatus enum
                avg_rating=r["overall"] if r else None,
                rating_count=r["count"] if r else 0,
                open_internships=opens.get(c.id, 0),
            )
        )
    return out


async def detail(session: AsyncSession, storage: Storage, company: CompanyModel) -> s.Company:
    (summary,) = await summaries(session, storage, [company])
    ratings = (await repo.rating_summaries(session, [company.id])).get(company.id)
    return s.Company(
        **summary.model_dump(),
        website=company.website,
        description=company.description,
        contact_person_name=company.contact_person_name,
        contact_email=company.contact_email,
        contact_phone=company.contact_phone,
        archived_at=company.archived_at,
        created_at=company.created_at,
        rating_summary=s.RatingSummary(**ratings) if ratings else s.RatingSummary(),
        internship_count=await repo.internship_count(session, company.id),
    )


def _snap(c: CompanyModel) -> dict[str, Any]:
    return {
        "name": c.name,
        "registration_number": c.registration_number,
        "location": c.location,
        "industry": c.industry,
        "status": c.status,
        "contact_email": c.contact_email,
    }


# ---- access helpers --------------------------------------------------------------------------------------------
async def get_visible(session: AsyncSession, user: User, company_id: uuid.UUID) -> CompanyModel:
    """Company the viewer may see, else 404 (hides existence of PENDING / ARCHIVED companies)."""
    company = await repo.get(session, company_id)
    if company is None:
        raise not_found("Company not found")
    if user.role == "ADMIN":
        return company
    member_cid = await member_company_id(session, user)
    visible = (company.status == "ACTIVE" and company.archived_at is None) or (
        (user.role == "FACULTY" and company.created_by == user.id)
        or (user.role == "COMPANY" and member_cid == company.id)
    )
    if not visible:
        raise not_found("Company not found")
    return company


async def _get_or_404(session: AsyncSession, company_id: uuid.UUID) -> CompanyModel:
    company = await repo.get(session, company_id)
    if company is None:
        raise not_found("Company not found")
    return company


async def _validate_logo(session: AsyncSession, actor: User, document_id: uuid.UUID | None) -> None:
    if document_id is None:
        return
    docs = await repo.logo_documents(session, [document_id])
    doc = docs.get(document_id)
    if doc is None or doc.kind != "LOGO" or (doc.owner_id != actor.id and actor.role != "ADMIN"):
        raise unprocessable(
            "Logo document not found",
            details=[{"field": "logo_document_id", "message": "Upload the logo first (kind LOGO) and use its id"}],
        )


# ---- queries ------------------------------------------------------------------------------------------------------
async def list_companies(
    session: AsyncSession,
    storage: Storage,
    user: User,
    params: PageParams,
    q: str | None,
    location: str | None,
    industry: str | None,
    status: str | None,
) -> dict[str, Any]:
    member_cid = await member_company_id(session, user)
    stmt = repo.list_query(user, member_cid, q, location, industry, status)
    rows, total = await paginate(session, stmt, params)
    return make_page(await summaries(session, storage, rows), total, params)


async def get_company(session: AsyncSession, storage: Storage, user: User, company_id: uuid.UUID) -> s.Company:
    return await detail(session, storage, await get_visible(session, user, company_id))


async def ratings(session: AsyncSession, user: User, company_id: uuid.UUID) -> s.CompanyRatingsResponse:
    company = await get_visible(session, user, company_id)
    r = (await repo.rating_summaries(session, [company.id])).get(company.id)
    recent = []
    for fb, student_name, internship_title in await repo.recent_feedback(session, company.id):
        recent.append(
            s.RecentRating(
                id=fb.id,
                overall=fb.overall,
                comments=fb.comments,
                student_name=None if (fb.is_anonymous and user.role != "ADMIN") else student_name,
                internship_title=internship_title,
                created_at=fb.created_at,
            )
        )
    return s.CompanyRatingsResponse(summary=s.RatingSummary(**r) if r else s.RatingSummary(), recent=recent)


async def list_members(session: AsyncSession, user: User, company_id: uuid.UUID) -> list[s.CompanyMember]:
    company = await _get_or_404(session, company_id)
    if user.role != "ADMIN" and (await member_company_id(session, user)) != company.id:
        raise not_found("Company not found")
    return [
        s.CompanyMember(user_id=m.user_id, full_name=u.full_name, email=u.email, job_title=m.job_title)
        for m, u in await repo.members(session, company.id)
    ]


async def list_internships(
    session: AsyncSession, storage: Storage, user: User, company_id: uuid.UUID, params: PageParams
) -> dict[str, Any]:
    company = await get_visible(session, user, company_id)
    member_cid = await member_company_id(session, user)
    rows, total = await paginate(
        session, repo.internships_query(user, member_cid, company.id), params, scalars=False
    )
    (summary,) = await summaries(session, storage, [company])
    ref = s.CompanyRef(id=company.id, name=company.name, logo_url=summary.logo_url, avg_rating=summary.avg_rating)
    items = []
    for internship, is_saved, app_count in rows:
        owns = (
            user.role == "ADMIN"
            or internship.posted_by == user.id
            or (user.role == "COMPANY" and member_cid == internship.company_id)
        )
        items.append(
            s.CompanyInternshipItem(
                id=internship.id,
                title=internship.title,
                domain=internship.domain,
                location=internship.location,
                work_mode=internship.work_mode,  # type: ignore[arg-type]  # validated into WorkMode
                stipend_monthly=internship.stipend_monthly,
                currency=internship.currency,
                duration_weeks=internship.duration_weeks,
                start_date=internship.start_date,
                end_date=internship.end_date,
                application_deadline=internship.application_deadline,
                status=internship.status,
                skills=list(internship.skills or []),
                company=ref,
                is_saved=bool(is_saved),
                application_count=int(app_count) if owns else None,
                archived_at=internship.archived_at,
                created_at=internship.created_at,
            )
        )
    return make_page(items, total, params)


# ---- commands ------------------------------------------------------------------------------------------------------
async def create_company(
    session: AsyncSession, storage: Storage, user: User, data: s.CompanyCreateRequest
) -> s.Company:
    await _validate_logo(session, user, data.logo_document_id)
    company = CompanyModel(
        id=uuid.uuid4(),
        name=data.name,
        registration_number=data.registration_number,
        industry=data.industry,
        location=data.location,
        website=data.website,
        description=data.description,
        logo_document_id=data.logo_document_id,
        contact_person_name=data.contact_person_name,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        status="ACTIVE",
        created_by=user.id,
    )
    session.add(company)
    await session.flush()  # uq_companies_registration_number -> 409 DUPLICATE_REGISTRATION_NUMBER
    audit(session, user, "company.create", "company", company.id, after=_snap(company))
    return await detail(session, storage, company)


async def update_company(
    session: AsyncSession, storage: Storage, user: User, company_id: uuid.UUID, data: s.CompanyUpdateRequest
) -> s.Company:
    company = await get_visible(session, user, company_id)
    allowed = (
        user.role == "ADMIN"
        or (user.role == "FACULTY" and company.created_by == user.id)
        or (user.role == "COMPANY" and (await member_company_id(session, user)) == company.id)
    )
    if not allowed:
        raise forbidden()
    before = _snap(company)
    fields = data.model_fields_set
    if (
        "registration_number" in fields
        and data.registration_number is not None
        and data.registration_number != company.registration_number
        and user.role != "ADMIN"
    ):
        raise forbidden("Only an administrator can change the registration number")
    if "logo_document_id" in fields:
        await _validate_logo(session, user, data.logo_document_id)
    not_nullable = {"name", "registration_number", "location", "contact_person_name", "contact_email"}
    for field in fields:
        value = getattr(data, field)
        if value is None and field in not_nullable:
            continue
        setattr(company, field, value)
    await session.flush()
    audit(session, user, "company.update", "company", company.id, before=before, after=_snap(company))
    return await detail(session, storage, company)


async def approve(session: AsyncSession, storage: Storage, admin: User, company_id: uuid.UUID) -> s.Company:
    company = await _get_or_404(session, company_id)
    if company.status != "PENDING":
        raise AppError(409, "INVALID_STATUS_TRANSITION", f"Cannot approve a company with status {company.status}")
    company.status = "ACTIVE"
    await session.flush()
    audit(session, admin, "company.approve", "company", company.id, before={"status": "PENDING"}, after={"status": "ACTIVE"})
    for uid in await repo.member_user_ids(session, company.id):
        notify(
            session,
            uid,
            "COMPANY_APPROVED",
            "Company approved",
            f"{company.name} has been approved. You can now post internships.",
            "/company/internships",
            {"company_id": str(company.id)},
        )
    return await detail(session, storage, company)


async def archive(session: AsyncSession, storage: Storage, admin: User, company_id: uuid.UUID) -> s.Company:
    company = await _get_or_404(session, company_id)
    if company.status == "ARCHIVED":
        raise AppError(409, "INVALID_STATUS_TRANSITION", "Company is already archived")
    before = {"status": company.status}
    company.status = "ARCHIVED"
    company.archived_at = utcnow()
    await session.flush()
    audit(session, admin, "company.archive", "company", company.id, before=before, after={"status": "ARCHIVED"})
    return await detail(session, storage, company)


async def restore(session: AsyncSession, storage: Storage, admin: User, company_id: uuid.UUID) -> s.Company:
    company = await _get_or_404(session, company_id)
    if company.status != "ARCHIVED":
        raise AppError(409, "INVALID_STATUS_TRANSITION", "Only archived companies can be restored")
    company.status = "ACTIVE"
    company.archived_at = None
    await session.flush()
    audit(session, admin, "company.restore", "company", company.id, before={"status": "ARCHIVED"}, after={"status": "ACTIVE"})
    return await detail(session, storage, company)


async def delete_company(session: AsyncSession, admin: User, company_id: uuid.UUID) -> None:
    company = await _get_or_404(session, company_id)
    if await repo.internship_count(session, company.id) > 0:
        raise conflict("This company has internships; archive it instead", "IN_USE")
    snap = _snap(company)
    await session.execute(delete(CompanyModel).where(CompanyModel.id == company.id))
    await session.flush()
    audit(session, admin, "company.delete", "company", company_id, before=snap)
