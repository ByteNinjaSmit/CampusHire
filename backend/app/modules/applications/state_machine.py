"""Application state machine (plan 3.8).

Public API for other modules (WP3c interviews imports this):

    transition_application(session, application_id, to_status, actor, note=None, system=False, offer_details=None)
        -> Application

* Locks the row (SELECT ... FOR UPDATE), validates against the transition table, writes
  ``application_status_history``, sets ``status_changed_at``, calls ``notify()`` / ``queue_email()`` / ``audit()``.
* ``system=True`` is for automatic moves (SHORTLISTED <-> INTERVIEW done by the interview module). It skips the
  ownership check and is the only way to perform the "system only" transitions. ``actor`` is then the user
  that caused the move (may be ``None``).
* Raises ``AppError``: 404 NOT_FOUND (outside scope), 409 INVALID_STATUS_TRANSITION, 422 VALIDATION_ERROR (offer).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import utcnow
from app.core.errors import AppError, conflict, not_found, unprocessable
from app.core.permissions import can_manage_internship
from app.core.side_effects import audit, notify, queue_email
from app.modules.applications.models import Application, ApplicationStatusHistory
from app.modules.companies.models import Company, CompanyMember
from app.modules.internships.models import Internship
from app.modules.users.models import User

PENDING, UNDER_REVIEW, SHORTLISTED, INTERVIEW = "PENDING", "UNDER_REVIEW", "SHORTLISTED", "INTERVIEW"
ACCEPTED, REJECTED, WITHDRAWN = "ACCEPTED", "REJECTED", "WITHDRAWN"
ALL_STATUSES = (PENDING, UNDER_REVIEW, SHORTLISTED, INTERVIEW, ACCEPTED, REJECTED, WITHDRAWN)

# Staff (FACULTY owner / COMPANY owner / ADMIN) transitions, excluding the system-only moves.
TRANSITIONS: dict[str, set[str]] = {
    PENDING: {UNDER_REVIEW, SHORTLISTED, REJECTED},
    UNDER_REVIEW: {SHORTLISTED, REJECTED},
    SHORTLISTED: {ACCEPTED, REJECTED},
    INTERVIEW: {ACCEPTED, REJECTED},
    ACCEPTED: set(),
    REJECTED: set(),
    WITHDRAWN: set(),
}
# Moves that only the system (interview module) may perform.
SYSTEM_TRANSITIONS: dict[str, set[str]] = {
    SHORTLISTED: {INTERVIEW},
    INTERVIEW: {SHORTLISTED},
}
# STUDENT owner: any non-terminal (incl. ACCEPTED = decline the offer) -> WITHDRAWN.
STUDENT_TRANSITIONS: dict[str, set[str]] = {
    PENDING: {WITHDRAWN},
    UNDER_REVIEW: {WITHDRAWN},
    SHORTLISTED: {WITHDRAWN},
    INTERVIEW: {WITHDRAWN},
    ACCEPTED: {WITHDRAWN},
    REJECTED: set(),
    WITHDRAWN: set(),
}

TERMINAL = {REJECTED, WITHDRAWN}

STATUS_LABELS = {
    PENDING: "Pending",
    UNDER_REVIEW: "Under review",
    SHORTLISTED: "Shortlisted",
    INTERVIEW: "Interview stage",
    ACCEPTED: "Accepted",
    REJECTED: "Rejected",
    WITHDRAWN: "Withdrawn",
}


def allowed_targets(role: str, from_status: str, *, system: bool = False) -> set[str]:
    """Statuses ``role`` may move an application in ``from_status`` to."""
    if role == "STUDENT":
        return set(STUDENT_TRANSITIONS.get(from_status, set()))
    targets = set(TRANSITIONS.get(from_status, set()))
    if system:
        targets |= SYSTEM_TRANSITIONS.get(from_status, set())
    return targets


def _staff_link(user: User, internship_id: uuid.UUID) -> str:
    if user.role == "COMPANY":
        return f"/company/review/{internship_id}"
    if user.role == "ADMIN":
        return "/admin/applications"
    return f"/faculty/review/{internship_id}"


async def internship_owner_users(session: AsyncSession, internship: Internship) -> list[User]:
    """Users owning the internship: the poster plus all COMPANY members of its company."""
    ids = {internship.posted_by}
    member_ids = (
        await session.execute(select(CompanyMember.user_id).where(CompanyMember.company_id == internship.company_id))
    ).scalars().all()
    ids.update(member_ids)
    rows = (await session.execute(select(User).where(User.id.in_(ids), User.is_active.is_(True)))).scalars().all()
    return list(rows)


async def notify_owners(
    session: AsyncSession,
    internship: Internship,
    *,
    type: str,  # noqa: A002
    title: str,
    body: str,
    data: dict[str, Any],
    exclude: uuid.UUID | None = None,
) -> None:
    for owner in await internship_owner_users(session, internship):
        if owner.id == exclude:
            continue
        notify(session, owner.id, type, title, body, _staff_link(owner, internship.id), data)


def _status_note(status: str, internship_title: str) -> tuple[str, str]:
    label = STATUS_LABELS.get(status, status)
    titles = {
        UNDER_REVIEW: "Your application is under review",
        SHORTLISTED: "You have been shortlisted",
        INTERVIEW: "Interview stage reached",
        ACCEPTED: "Congratulations! Your application was accepted",
        REJECTED: "Your application was not selected",
        WITHDRAWN: "Application withdrawn",
    }
    return titles.get(status, f"Application status: {label}"), f"{internship_title}: {label}"


async def transition_application(
    session: AsyncSession,
    application_id: uuid.UUID,
    to_status: str,
    actor: User | None,
    note: str | None = None,
    system: bool = False,
    offer_details: dict[str, Any] | None = None,
) -> Application:
    to_status = str(getattr(to_status, "value", to_status))
    if to_status not in ALL_STATUSES:
        raise unprocessable(
            "Invalid status", details=[{"field": "status", "message": f"Must be one of {', '.join(ALL_STATUSES)}"}]
        )
    if actor is None and not system:
        raise AppError(500, "INTERNAL_ERROR", "actor required for non-system transitions")

    app = (
        await session.execute(
            select(Application)
            .where(Application.id == application_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if app is None:
        raise not_found("Application not found")
    internship = (await session.execute(select(Internship).where(Internship.id == app.internship_id))).scalar_one()

    # ---- scope -------------------------------------------------------------------------------
    if not system:
        assert actor is not None
        if actor.role == "STUDENT":
            if app.student_id != actor.id:
                raise not_found("Application not found")
        elif not await can_manage_internship(session, actor, internship):
            raise not_found("Application not found")

    # ---- transition table ----------------------------------------------------------------------
    role = actor.role if (actor is not None and not system) else "SYSTEM"
    allowed = allowed_targets("STUDENT" if role == "STUDENT" else role, app.status, system=system)
    if to_status not in allowed:
        raise conflict(
            f"Cannot move application from {app.status} to {to_status}", code="INVALID_STATUS_TRANSITION"
        )
    if to_status == ACCEPTED and not offer_details:
        raise unprocessable(
            "offer_details are required to accept an application",
            details=[{"field": "offer_details", "message": "Required when accepting an application"}],
        )

    # ---- apply --------------------------------------------------------------------------------
    from_status = app.status
    now = utcnow()
    app.status = to_status
    app.status_changed_at = now
    if to_status == ACCEPTED:
        app.offer_details = offer_details
        app.decision_note = note
    elif to_status == REJECTED:
        app.decision_note = note
    elif to_status == WITHDRAWN:
        app.withdrawn_reason = note
    session.add(
        ApplicationStatusHistory(
            application_id=app.id,
            from_status=from_status,
            to_status=to_status,
            changed_by=actor.id if actor is not None else None,
            note=note,
            created_at=now,
        )
    )
    await session.flush()

    # ---- side effects -----------------------------------------------------------------------------
    student_user = (await session.execute(select(User).where(User.id == app.student_id))).scalar_one()
    company = (await session.execute(select(Company).where(Company.id == internship.company_id))).scalar_one()
    title, body = _status_note(to_status, internship.title)
    link = f"/student/applications/{app.id}"
    data = {"application_id": str(app.id), "internship_id": str(internship.id), "status": to_status}
    notify(session, student_user.id, "APPLICATION_STATUS", title, body, link, data)
    queue_email(
        session,
        "application_status",
        student_user.email,
        {
            "student_name": student_user.full_name,
            "internship_title": internship.title,
            "company_name": company.name,
            "status": to_status,
            "status_label": STATUS_LABELS[to_status],
            "note": note,
            "link": link,
            "offer_details": offer_details if to_status == ACCEPTED else None,
        },
    )
    if to_status == WITHDRAWN and not system:
        await notify_owners(
            session,
            internship,
            type="APPLICATION_WITHDRAWN",
            title="An applicant withdrew",
            body=f"{student_user.full_name} withdrew from {internship.title}",
            data=data,
            exclude=actor.id if actor is not None else None,
        )
    audit(
        session,
        actor,
        "application.status_change",
        "application",
        app.id,
        before={"status": from_status},
        after={"status": to_status, "note": note, "system": system},
    )
    return app
