"""Ownership helpers shared by WP3/WP4 services (plan 4.4).

* Internship owner: ``posted_by`` == user, or a COMPANY member of the internship's company. ADMIN manages all.
* Application visibility for staff: the application's internship is owned by them.

"Out of scope" should be reported as 404 NOT_FOUND by callers (prevents id enumeration).
"""

import uuid
from typing import Any

from sqlalchemy import Select, or_, select

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.applications.models import Application
from app.modules.companies.models import CompanyMember
from app.modules.internships.models import Internship
from app.modules.users.models import User


async def member_company_id(session: AsyncSession, user: User) -> uuid.UUID | None:
    """company_id the COMPANY user belongs to (None for other roles / no membership)."""
    if user.role != "COMPANY":
        return None
    return (
        await session.execute(select(CompanyMember.company_id).where(CompanyMember.user_id == user.id))
    ).scalar_one_or_none()


async def is_company_member(session: AsyncSession, user: User, company_id: uuid.UUID) -> bool:
    return (await member_company_id(session, user)) == company_id


def owned_internships_clause(user: User, company_id: uuid.UUID | None) -> Any:
    """SQL boolean clause over ``Internship`` selecting rows the user owns. ADMIN -> true()."""
    from sqlalchemy import true

    if user.role == "ADMIN":
        return true()
    clauses = [Internship.posted_by == user.id]
    if user.role == "COMPANY" and company_id is not None:
        clauses.append(Internship.company_id == company_id)
    return or_(*clauses)


async def owned_internship_ids(session: AsyncSession, user: User) -> Select[Any]:
    """``select(Internship.id)`` for internships the staff user owns (use in ``.in_()``)."""
    company_id = await member_company_id(session, user)
    return select(Internship.id).where(owned_internships_clause(user, company_id))


async def can_manage_internship(session: AsyncSession, user: User, internship: Internship) -> bool:
    if user.role == "ADMIN":
        return True
    if internship.posted_by == user.id:
        return True
    if user.role == "COMPANY":
        return (await member_company_id(session, user)) == internship.company_id
    return False


async def can_view_application(session: AsyncSession, user: User, application: Application) -> bool:
    """Student sees own, staff see applications to internships they own, ADMIN sees all."""
    if user.role == "ADMIN":
        return True
    if user.role == "STUDENT":
        return application.student_id == user.id
    if user.role in ("FACULTY", "COMPANY"):
        internship = (
            await session.execute(select(Internship).where(Internship.id == application.internship_id))
        ).scalar_one_or_none()
        return internship is not None and await can_manage_internship(session, user, internship)
    return False
