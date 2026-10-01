"""``emails.send(template, to, context)``: Jinja2 HTML + text multipart mail via smtplib (mailpit in dev).

Producers call ``side_effects.queue_email(session, template, to, context)``; ``context`` is JSON, so datetimes
are ISO-8601 strings. Every template tolerates missing keys (they render as empty / a fallback). Keys used:

=====================  ==========================================================================================
verify_email           full_name, verify_url, expires_hours
reset_password         full_name, reset_url, expires_hours
application_submitted  full_name, internship_title, company_name, link?
application_status     full_name, internship_title, company_name, status, note?, link?
interview_*            full_name, internship_title, company_name, scheduled_at (ISO), duration_minutes, mode,
                       location?, meeting_link?, interviewer_name?, interview_id?, link?,
                       cancelled: reason? | rescheduled: old_scheduled_at?, reschedule_count?
internship_approved    full_name, internship_title, company_name?, link?
internship_rejected    full_name, internship_title, reason?, link?
report_ready           full_name, report_title, format?, download_url? / link?
import_finished        full_name, rows_ok, rows_failed, link?
=====================  ==========================================================================================

``interview_scheduled`` / ``interview_rescheduled`` / ``interview_reminder`` carry an ``.ics`` invite
(METHOD:REQUEST) and ``interview_cancelled`` a METHOD:CANCEL one, provided ``scheduled_at`` is present.
"""

from __future__ import annotations

import hashlib
import logging
import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound, Undefined, select_autoescape

from app.core.celery_app import celery_app
from app.core.config import settings

log = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "emails"

SUBJECTS: dict[str, str] = {
    "verify_email": "Verify your CampusHire email address",
    "reset_password": "Reset your CampusHire password",
    "application_submitted": "Application received: {{ internship_title }}",
    "application_status": "Application update: {{ internship_title }} is now {{ (status or '')|replace('_', ' ')|title }}",
    "interview_scheduled": "Interview scheduled: {{ internship_title }}",
    "interview_rescheduled": "Interview rescheduled: {{ internship_title }}",
    "interview_cancelled": "Interview cancelled: {{ internship_title }}",
    "interview_reminder": "Reminder: your interview for {{ internship_title }} is within 24 hours",
    "internship_approved": "Your internship was approved: {{ internship_title }}",
    "internship_rejected": "Your internship was not approved: {{ internship_title }}",
    "report_ready": "Your report is ready: {{ report_title }}",
    "import_finished": "Data import finished",
}
TEMPLATES = tuple(SUBJECTS)
ICS_TEMPLATES = {"interview_scheduled", "interview_rescheduled", "interview_reminder", "interview_cancelled"}


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _fmt_dt(value: Any) -> str:
    dt = _parse_dt(value)
    return dt.astimezone(UTC).strftime("%a, %d %b %Y, %H:%M UTC") if dt else (str(value) if value else "")


def _build_env(strict: bool = False) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"], default=False),
        undefined=StrictUndefined if strict else Undefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["dt"] = _fmt_dt
    return env


_env = _build_env()
_subject_env = Environment(autoescape=False, undefined=Undefined)


@dataclass
class RenderedEmail:
    subject: str
    html: str
    text: str


def render_email(template: str, context: dict[str, Any] | None = None) -> RenderedEmail:
    """Render subject + HTML + text for ``template``. Raises ``ValueError`` for an unknown template."""
    if template not in SUBJECTS:
        raise ValueError(f"unknown email template: {template!r}")
    ctx = {**(context or {}), "frontend_url": settings.FRONTEND_URL, "template_name": template}
    try:
        html = _env.get_template(f"{template}.html").render(**ctx)
        text = _env.get_template(f"{template}.txt").render(**ctx)
    except TemplateNotFound as exc:
        raise ValueError(f"email template files missing: {exc.name}") from exc
    subject = _subject_env.from_string(SUBJECTS[template]).render(**ctx)
    return RenderedEmail(" ".join(subject.split()), html, text)


# ---- iCalendar -----------------------------------------------------------------------------------
def _ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n")
    )


def _ics_fold(line: str) -> str:
    """Fold at 75 octets (RFC 5545 3.1), never splitting a multi-byte character."""
    raw = line.encode()
    if len(raw) <= 75:
        return line
    parts: list[str] = []
    current = ""
    limit = 75
    for ch in line:
        if len((current + ch).encode()) > limit:
            parts.append(current)
            current, limit = ch, 74  # continuation lines start with one space
        else:
            current += ch
    parts.append(current)
    return "\r\n ".join(parts)


def _ics_dt(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def build_ics(template: str, context: dict[str, Any]) -> bytes | None:
    """An RFC 5545 invite for the interview templates, or None when there is nothing to schedule."""
    if template not in ICS_TEMPLATES:
        return None
    start = _parse_dt(context.get("scheduled_at"))
    if start is None:
        return None
    try:
        minutes = int(context.get("duration_minutes") or 30)
    except (TypeError, ValueError):
        minutes = 30
    cancelled = template == "interview_cancelled"
    seed = str(context.get("interview_id") or f"{context.get('internship_title')}|{context.get('full_name')}")
    uid = f"interview-{hashlib.sha1(seed.encode()).hexdigest()[:24]}@campushire.dev"  # noqa: S324 - not security relevant
    sequence = int(context.get("reschedule_count") or 0) + (1 if cancelled else 0)
    title = context.get("internship_title") or "Internship"
    company = context.get("company_name")
    summary = f"Interview: {title}" + (f" ({company})" if company else "")
    where = context.get("location") or context.get("meeting_link") or ""
    desc_lines = [
        f"Mode: {context.get('mode')}" if context.get("mode") else "",
        f"Interviewer: {context.get('interviewer_name')}" if context.get("interviewer_name") else "",
        f"Meeting link: {context.get('meeting_link')}" if context.get("meeting_link") else "",
    ]
    description = "\n".join(line for line in desc_lines if line)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//CampusHire//Interviews//EN",
        "CALSCALE:GREGORIAN",
        f"METHOD:{'CANCEL' if cancelled else 'REQUEST'}",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_ics_dt(datetime.now(UTC))}",
        f"DTSTART:{_ics_dt(start)}",
        f"DTEND:{_ics_dt(start + timedelta(minutes=minutes))}",
        f"SEQUENCE:{sequence}",
        f"SUMMARY:{_ics_escape(summary)}",
        f"STATUS:{'CANCELLED' if cancelled else 'CONFIRMED'}",
    ]
    if where:
        lines.append(f"LOCATION:{_ics_escape(str(where))}")
    if description:
        lines.append(f"DESCRIPTION:{_ics_escape(description)}")
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return ("\r\n".join(_ics_fold(line) for line in lines) + "\r\n").encode()


def build_message(template: str, to: str, context: dict[str, Any] | None = None) -> EmailMessage:
    context = context or {}
    rendered = render_email(template, context)
    msg = EmailMessage()
    msg["From"] = settings.MAIL_FROM
    msg["To"] = to
    msg["Subject"] = rendered.subject
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = make_msgid(domain="campushire.dev")
    msg.set_content(rendered.text)
    msg.add_alternative(rendered.html, subtype="html")
    ics = build_ics(template, context)
    if ics is not None:
        method = "CANCEL" if template == "interview_cancelled" else "REQUEST"
        msg.add_attachment(
            ics,
            maintype="text",
            subtype="calendar",
            filename="interview.ics",
            params={"method": method, "charset": "utf-8"},
        )
    return msg


def deliver(msg: EmailMessage) -> None:
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        smtp.send_message(msg)


@celery_app.task(
    name="emails.send",
    bind=True,
    max_retries=4,
    acks_late=True,
)
def send_email(self, template: str, to: str, context: dict[str, Any] | None = None) -> dict[str, str]:
    """Render and send one e-mail. SMTP / network errors are retried with exponential backoff (10 s, 20 s, ...);
    an unknown template or a rejected recipient is a permanent failure."""
    msg = build_message(template, to, context)  # ValueError (unknown template) is not retried
    try:
        deliver(msg)
    except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused):
        log.exception("email %s to %s refused", template, to)
        raise
    except (smtplib.SMTPException, OSError) as exc:
        log.warning("email %s to %s failed (%s), retry %d", template, to, exc, self.request.retries)
        raise self.retry(exc=exc, countdown=10 * 2**self.request.retries) from exc
    log.info("email %s sent to %s", template, to)
    return {"template": template, "to": to, "subject": str(msg["Subject"])}
