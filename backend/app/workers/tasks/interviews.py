"""``interviews.send_reminders``: one reminder per interview, once it is less than 24 h away (beat: every 15 min)."""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core import side_effects
from app.core.base import utcnow
from app.core.celery_app import celery_app
from app.modules.applications.models import Application
from app.modules.companies.models import Company
from app.modules.internships.models import Internship
from app.modules.interviews.models import Interview
from app.modules.users.models import User
from app.workers.runtime import iso_z, run_async, worker_session

log = logging.getLogger(__name__)

REMINDER_WINDOW = timedelta(hours=24)


async def send_reminders(session: AsyncSession) -> int:
    """Notify + e-mail the student (and the interviewer) for every SCHEDULED/RESCHEDULED interview that starts
    within 24 h and has no reminder yet; stamps ``reminder_sent_at`` so each interview is reminded once.
    Returns the number of interviews processed."""
    now = utcnow()
    interviewer = aliased(User)
    rows = (
        await session.execute(
            select(Interview, Internship.title, Company.name, User.id, User.email, User.full_name, interviewer.email)
            .join(Application, Application.id == Interview.application_id)
            .join(Internship, Internship.id == Application.internship_id)
            .join(Company, Company.id == Internship.company_id)
            .join(User, User.id == Application.student_id)
            .outerjoin(interviewer, interviewer.id == Interview.interviewer_user_id)
            .where(
                Interview.status.in_(("SCHEDULED", "RESCHEDULED")),
                Interview.reminder_sent_at.is_(None),
                Interview.scheduled_at > now,
                Interview.scheduled_at <= now + REMINDER_WINDOW,
                Application.status.in_(("INTERVIEW", "SHORTLISTED")),
            )
            .order_by(Interview.scheduled_at)
            .with_for_update(of=Interview, skip_locked=True)
        )
    ).all()
    for iv, title, company, student_id, student_email, student_name, interviewer_user_email in rows:
        ctx = {
            "internship_title": title,
            "company_name": company,
            "scheduled_at": iso_z(iv.scheduled_at),
            "duration_minutes": iv.duration_minutes,
            "mode": iv.mode,
            "location": iv.location,
            "meeting_link": iv.meeting_link,
            "interviewer_name": iv.interviewer_name,
            "interview_id": str(iv.id),
            "reschedule_count": iv.reschedule_count,
            "link": "/student/interviews",
        }
        when = iv.scheduled_at.strftime("%d %b %Y, %H:%M UTC")
        side_effects.notify(
            session,
            student_id,
            "INTERVIEW_REMINDER",
            "Interview reminder",
            f"Your interview for {title} ({company}) is on {when}.",
            link="/student/interviews",
            data={"interview_id": str(iv.id), "application_id": str(iv.application_id)},
        )
        side_effects.queue_email(session, "interview_reminder", student_email, {**ctx, "full_name": student_name})
        recipient = interviewer_user_email or iv.interviewer_email
        if iv.interviewer_user_id:
            side_effects.notify(
                session,
                iv.interviewer_user_id,
                "INTERVIEW_REMINDER",
                "Interview reminder",
                f"You interview a candidate for {title} on {when}.",
                data={"interview_id": str(iv.id), "application_id": str(iv.application_id)},
            )
        if recipient and recipient.lower() != student_email.lower():
            side_effects.queue_email(
                session, "interview_reminder", recipient, {**ctx, "full_name": iv.interviewer_name, "link": None}
            )
        iv.reminder_sent_at = now
    return len(rows)


@celery_app.task(name="interviews.send_reminders")
def send_interview_reminders() -> int:
    async def _run() -> int:
        async with worker_session() as session:
            return await send_reminders(session)

    sent = run_async(_run())
    if sent:
        log.info("sent reminders for %d interview(s)", sent)
    return sent
