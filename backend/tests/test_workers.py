"""WP4a workers: task registry + beat, e-mail rendering / .ics / SMTP, maintenance tasks, reminders, job wrappers."""

import asyncio
import smtplib
import socket
import sys
import types
import uuid
from datetime import UTC, datetime, timedelta
from email import message_from_bytes, policy

import httpx
import pytest
from celery.schedules import crontab
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import side_effects
from app.core.base import utcnow
from app.core.config import settings
from app.modules.admin.models import CompliancePolicy, Job, PolicyViolation
from app.modules.auth.models import RefreshToken, UserToken
from app.modules.documents.models import Document
from app.modules.internships.models import Internship
from app.modules.interviews.models import Interview
from app.modules.notifications.models import Notification
from app.workers import main as worker_main
from app.workers import runtime
from app.workers.tasks import data as data_tasks
from app.workers.tasks import emails, interviews, maintenance
from app.workers.tasks import reports as report_tasks
from tests.factories import (
    make_application,
    make_company,
    make_faculty,
    make_internship,
    make_resume,
    make_student,
    make_user,
)

HOURS = timedelta(hours=1)
DAYS = timedelta(days=1)


# ---- registry / beat --------------------------------------------------------------------------------
def test_task_names_registered():
    names = set(worker_main.celery_app.tasks)
    assert {
        "emails.send",
        "reports.export",
        "data.export",
        "data.import",
        "maintenance.compliance_scan",
        "maintenance.close_expired_internships",
        "maintenance.cleanup_tokens",
        "maintenance.purge_pending_uploads",
        "interviews.send_reminders",
    } <= names
    assert worker_main.app is worker_main.celery_app


def test_beat_schedule():
    sched = {v["task"]: v["schedule"] for v in worker_main.celery_app.conf.beat_schedule.values()}
    assert set(sched) == {
        "maintenance.compliance_scan",
        "maintenance.close_expired_internships",
        "maintenance.cleanup_tokens",
        "maintenance.purge_pending_uploads",
        "interviews.send_reminders",
    }
    assert sched["maintenance.compliance_scan"] == crontab(hour=2, minute=0)
    assert sched["maintenance.close_expired_internships"] == crontab(minute=0)
    assert sched["interviews.send_reminders"] == crontab(minute="*/15")
    assert worker_main.celery_app.conf.timezone == "UTC"


# ---- e-mail rendering -------------------------------------------------------------------------------
_WHEN = (datetime.now(UTC) + timedelta(days=3)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
_INTERVIEW_CTX = {
    "full_name": "Asha Rao",
    "internship_title": "Backend Intern",
    "company_name": "Acme Corp",
    "scheduled_at": _WHEN,
    "duration_minutes": 45,
    "mode": "ONLINE",
    "meeting_link": "https://meet.example.com/abc",
    "interviewer_name": "Ravi Kumar",
    "interview_id": "11111111-1111-1111-1111-111111111111",
}
_CONTEXTS = {
    "verify_email": {"full_name": "Asha Rao", "verify_url": "http://localhost:3000/verify-email?token=T1", "expires_hours": 24},
    "reset_password": {"full_name": "Asha Rao", "reset_url": "http://localhost:3000/reset-password?token=T2", "expires_hours": 1},
    "application_submitted": {"full_name": "Asha Rao", "internship_title": "Backend Intern", "company_name": "Acme Corp"},
    "application_status": {
        "full_name": "Asha Rao", "internship_title": "Backend Intern", "company_name": "Acme Corp",
        "status": "UNDER_REVIEW", "note": "Looks promising",
    },
    "interview_scheduled": _INTERVIEW_CTX,
    "interview_rescheduled": {**_INTERVIEW_CTX, "old_scheduled_at": _WHEN, "reschedule_count": 1},
    "interview_cancelled": {**_INTERVIEW_CTX, "reason": "Panel unavailable"},
    "interview_reminder": _INTERVIEW_CTX,
    "internship_approved": {"full_name": "Acme HR", "internship_title": "Backend Intern", "company_name": "Acme Corp"},
    "internship_rejected": {"full_name": "Acme HR", "internship_title": "Backend Intern", "reason": "Missing stipend details"},
    "report_ready": {"full_name": "Admin", "report_title": "Placement Summary", "format": "pdf", "download_url": "http://x/y"},
    "import_finished": {"full_name": "Admin", "rows_ok": 18, "rows_failed": 2},
}


def test_every_required_template_has_context_and_files():
    required = {
        "verify_email", "reset_password", "application_submitted", "application_status", "interview_scheduled",
        "interview_rescheduled", "interview_cancelled", "interview_reminder", "internship_approved",
        "internship_rejected", "report_ready", "import_finished",
    }
    assert required == set(emails.TEMPLATES) == set(_CONTEXTS)
    for name in required:
        assert (emails.TEMPLATE_DIR / f"{name}.html").is_file()
        assert (emails.TEMPLATE_DIR / f"{name}.txt").is_file()


@pytest.mark.parametrize("template", sorted(_CONTEXTS))
def test_render_html_and_text(template):
    r = emails.render_email(template, _CONTEXTS[template])
    assert r.subject and "\n" not in r.subject and "{{" not in r.subject
    assert "<html" in r.html and _CONTEXTS[template]["full_name"] in r.html
    assert _CONTEXTS[template]["full_name"] in r.text and "<" not in r.text and "{%" not in r.text
    assert "CampusHire" in r.html and "CampusHire" in r.text


def test_render_key_content():
    v = emails.render_email("verify_email", _CONTEXTS["verify_email"])
    assert "token=T1" in v.html and "token=T1" in v.text and "24 hours" in v.text
    s = emails.render_email("application_status", _CONTEXTS["application_status"])
    assert "Under Review" in s.subject and "Looks promising" in s.html
    i = emails.render_email("interview_scheduled", _INTERVIEW_CTX)
    assert "https://meet.example.com/abc" in i.html and "45 min" in i.text and "UTC" in i.text
    imp = emails.render_email("import_finished", _CONTEXTS["import_finished"])
    assert "18" in imp.text and "2" in imp.text


def test_html_autoescapes_user_input_text_does_not():
    r = emails.render_email("application_submitted", {"full_name": "<script>alert(1)</script>", "internship_title": "A&B"})
    assert "<script>" not in r.html and "&lt;script&gt;" in r.html and "A&amp;B" in r.html
    assert "<script>" in r.text  # plain text part is not HTML


def test_templates_tolerate_missing_context():
    for name in emails.TEMPLATES:
        r = emails.render_email(name, {})
        assert r.subject and r.html and r.text


def test_unknown_template_raises():
    with pytest.raises(ValueError):
        emails.render_email("nope", {})
    with pytest.raises(ValueError):
        emails.build_message("nope", "a@b.co", {})


# ---- .ics --------------------------------------------------------------------------------------------
def _parts(msg):
    return {p.get_content_type(): p for p in msg.walk() if not p.is_multipart()}


@pytest.mark.parametrize("template", ["interview_scheduled", "interview_rescheduled", "interview_reminder"])
def test_interview_email_has_alternative_parts_and_ics_request(template):
    msg = emails.build_message(template, "asha@example.com", _CONTEXTS[template])
    assert msg["To"] == "asha@example.com" and msg["From"] == settings.MAIL_FROM
    parts = _parts(msg)
    assert {"text/plain", "text/html", "text/calendar"} <= set(parts)
    cal = parts["text/calendar"]
    assert cal.get_filename() == "interview.ics" and cal.get_param("method") == "REQUEST"
    ics = cal.get_content()
    start = datetime.fromisoformat(_WHEN.replace("Z", "+00:00"))
    assert "BEGIN:VCALENDAR" in ics and "METHOD:REQUEST" in ics and "STATUS:CONFIRMED" in ics
    assert f"DTSTART:{start:%Y%m%dT%H%M%SZ}" in ics
    assert f"DTEND:{start + timedelta(minutes=45):%Y%m%dT%H%M%SZ}" in ics
    assert "SUMMARY:Interview: Backend Intern (Acme Corp)" in ics
    assert "LOCATION:https://meet.example.com/abc" in ics
    assert ics.endswith("END:VCALENDAR\r\n")


def test_cancelled_interview_ics_is_cancel_method():
    msg = emails.build_message("interview_cancelled", "asha@example.com", _CONTEXTS["interview_cancelled"])
    ics = _parts(msg)["text/calendar"].get_content()
    assert "METHOD:CANCEL" in ics and "STATUS:CANCELLED" in ics and "SEQUENCE:1" in ics
    # UID stays stable across scheduled -> cancelled so calendars update the same event
    uid = lambda m: next(line for line in _parts(m)["text/calendar"].get_content().splitlines() if line.startswith("UID:"))  # noqa: E731
    sched = emails.build_message("interview_scheduled", "asha@example.com", _INTERVIEW_CTX)
    assert uid(sched) == uid(msg)


def test_non_interview_emails_have_no_attachment_and_ics_needs_scheduled_at():
    assert "text/calendar" not in _parts(emails.build_message("verify_email", "a@b.co", _CONTEXTS["verify_email"]))
    no_time = {k: v for k, v in _INTERVIEW_CTX.items() if k != "scheduled_at"}
    assert "text/calendar" not in _parts(emails.build_message("interview_scheduled", "a@b.co", no_time))


def test_ics_escaping_and_folding():
    ctx = {**_INTERVIEW_CTX, "internship_title": "Data, Science; Intern \\ " + "x" * 120, "location": "Room 1\nBlock A"}
    ics = emails.build_ics("interview_scheduled", ctx)
    assert ics is not None
    raw_lines = ics.decode().split("\r\n")
    assert all(len(line.encode()) <= 75 for line in raw_lines)
    unfolded = ics.decode().replace("\r\n ", "")
    assert "Data\\, Science\\; Intern \\\\ " in unfolded and "LOCATION:Room 1\\nBlock A" in unfolded


# ---- SMTP delivery -----------------------------------------------------------------------------------
def test_send_email_task_delivers_rendered_message(monkeypatch):
    sent = []
    monkeypatch.setattr(emails, "deliver", sent.append)
    out = emails.send_email("interview_scheduled", "asha@example.com", _INTERVIEW_CTX)
    assert out["subject"].startswith("Interview scheduled") and len(sent) == 1
    assert sent[0]["To"] == "asha@example.com"


def test_send_email_retries_transient_smtp_errors(monkeypatch):
    class Retried(Exception):
        pass

    def boom(msg):
        raise smtplib.SMTPServerDisconnected("down")

    def fake_retry(exc=None, countdown=None, **kw):
        raise Retried(countdown)

    monkeypatch.setattr(emails, "deliver", boom)
    monkeypatch.setattr(emails.send_email, "retry", fake_retry)
    with pytest.raises(Retried) as ei:
        emails.send_email("verify_email", "a@b.co", _CONTEXTS["verify_email"])
    assert ei.value.args == (10,)  # first retry after 10 s


def test_send_email_does_not_retry_refused_recipient(monkeypatch):
    def refused(msg):
        raise smtplib.SMTPRecipientsRefused({"a@b.co": (550, b"no")})

    monkeypatch.setattr(emails, "deliver", refused)
    monkeypatch.setattr(emails.send_email, "retry", lambda **kw: pytest.fail("must not retry"))
    with pytest.raises(smtplib.SMTPRecipientsRefused):
        emails.send_email("verify_email", "a@b.co", _CONTEXTS["verify_email"])


def _mailpit() -> tuple[str, int, str] | None:
    try:
        with socket.create_connection(("localhost", 1025), timeout=1):
            pass
        httpx.get("http://localhost:8025/api/v1/info", timeout=2).raise_for_status()
    except (OSError, httpx.HTTPError):
        return None
    return "localhost", 1025, "http://localhost:8025"


@pytest.mark.skipif(_mailpit() is None, reason="mailpit not reachable on localhost:1025/8025")
def test_real_smtp_delivery_to_mailpit(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "localhost")
    monkeypatch.setattr(settings, "SMTP_PORT", 1025)
    to = f"wp4a-{uuid.uuid4().hex[:8]}@example.com"
    emails.send_email("interview_scheduled", to, _INTERVIEW_CTX)
    r = httpx.get("http://localhost:8025/api/v1/search", params={"query": f"to:{to}"}, timeout=5).json()
    assert r["messages_count"] == 1
    mid = r["messages"][0]["ID"]
    full = httpx.get(f"http://localhost:8025/api/v1/message/{mid}", timeout=5).json()
    assert full["Subject"].startswith("Interview scheduled")
    assert full["HTML"] and full["Text"]
    assert [a["FileName"] for a in full["Attachments"]] == ["interview.ics"]
    raw = httpx.get(f"http://localhost:8025/api/v1/message/{mid}/raw", timeout=5).content
    assert message_from_bytes(raw, policy=policy.default)["To"] == to
    httpx.delete("http://localhost:8025/api/v1/messages", json={"IDs": [mid]}, timeout=5)


# ---- maintenance: close_expired_internships ------------------------------------------------------------
async def test_close_expired_internships(db: AsyncSession, monkeypatch, captured):
    monkeypatch.setattr(side_effects, "dispatcher", captured)
    owner = await make_faculty(db)
    expired = await make_internship(db, owner, deadline_in_days=-2)
    live = await make_internship(db, owner, deadline_in_days=5)
    draft = await make_internship(db, owner, status="DRAFT", deadline_in_days=-2)
    archived = await make_internship(db, owner, deadline_in_days=-2, archived_at=utcnow())

    assert await maintenance.close_expired_internships(db) == 1
    await db.flush()
    await side_effects.flush(db)
    for i in (expired, live, draft, archived):
        await db.refresh(i)
    assert (expired.status, live.status, draft.status, archived.status) == ("CLOSED", "APPROVED", "DRAFT", "APPROVED")
    note = (await db.execute(select(Notification).where(Notification.user_id == owner.id))).scalar_one()
    assert note.type == "INTERNSHIP_CLOSED"
    assert await maintenance.close_expired_internships(db) == 0  # idempotent


# ---- maintenance: cleanup_tokens ----------------------------------------------------------------------
async def test_cleanup_tokens(db: AsyncSession):
    user = await make_user(db)
    now = utcnow()

    def utok(tag, expires, used=None):
        return UserToken(user_id=user.id, purpose="VERIFY_EMAIL", token_hash=tag * 64, expires_at=expires, used_at=used)

    def rtok(tag, expires, revoked=None):
        return RefreshToken(
            user_id=user.id, family_id=uuid.uuid4(), token_hash=tag * 64, expires_at=expires, revoked_at=revoked
        )

    db.add_all(
        [
            utok("a", now - 3 * DAYS),  # expired long ago -> delete
            utok("b", now + HOURS, used=now - 3 * DAYS),  # used long ago -> delete
            utok("c", now + HOURS),  # live -> keep
            utok("d", now - HOURS),  # expired within grace -> keep
            rtok("e", now - 3 * DAYS),  # expired long ago -> delete
            rtok("f", now + 5 * DAYS, revoked=now - 3 * DAYS),  # revoked but unexpired: reuse detection needs it
            rtok("g", now + 5 * DAYS),  # live
        ]
    )
    await db.flush()
    res = await maintenance.cleanup_tokens(db)
    assert res == {"user_tokens": 2, "refresh_tokens": 1}
    left_u = {t.token_hash[0] for t in (await db.execute(select(UserToken))).scalars()}
    left_r = {t.token_hash[0] for t in (await db.execute(select(RefreshToken))).scalars()}
    assert left_u == {"c", "d"} and left_r == {"f", "g"}


# ---- maintenance: purge_pending_uploads ---------------------------------------------------------------
async def test_purge_pending_uploads(db: AsyncSession, fake_storage):
    user = await make_student(db)
    stale = await make_resume(db, user, status="PENDING_UPLOAD")
    fresh = await make_resume(db, user, status="PENDING_UPLOAD")
    done = await make_resume(db, user, status="UPLOADED")
    old_done = await make_resume(db, user, status="UPLOADED")
    for d in (stale, old_done):
        await db.execute(update(Document).where(Document.id == d.id).values(created_at=utcnow() - 3 * HOURS))
    fake_storage.put(stale.object_key, b"%PDF-1.4 partial")

    assert await maintenance.purge_pending_uploads(db, delete_object=fake_storage.delete) == 1
    remaining = {d for d in (await db.execute(select(Document.id))).scalars()}
    assert remaining == {fresh.id, done.id, old_done.id}
    assert fake_storage.deleted == [stale.object_key] and not fake_storage.has(stale.object_key)


async def test_purge_pending_uploads_keeps_referenced_documents(db: AsyncSession, fake_storage):
    student = await make_student(db)
    owner = await make_faculty(db)
    internship = await make_internship(db, owner)
    resume = await make_resume(db, student, status="PENDING_UPLOAD")
    await make_application(db, student, internship, resume=resume)
    await db.execute(update(Document).where(Document.id == resume.id).values(created_at=utcnow() - 3 * HOURS))
    assert await maintenance.purge_pending_uploads(db, delete_object=fake_storage.delete) == 0


# ---- compliance scan ------------------------------------------------------------------------------------
async def _violations(db: AsyncSession) -> dict[str, set[uuid.UUID]]:
    rows = (
        await db.execute(
            select(CompliancePolicy.code, PolicyViolation.entity_id).join(
                PolicyViolation, PolicyViolation.policy_id == CompliancePolicy.id
            ).where(PolicyViolation.status == "OPEN")
        )
    ).all()
    out: dict[str, set[uuid.UUID]] = {}
    for code, eid in rows:
        out.setdefault(code, set()).add(eid)
    return out


async def test_compliance_scan_detects_every_policy_and_is_idempotent(db: AsyncSession):
    assert {p.code for p in (await db.execute(select(CompliancePolicy))).scalars()} >= set(maintenance.DETECTORS)
    student = await make_student(db)
    owner = await make_faculty(db)

    # 1. RESUME_UNVERIFIED_7D: pending 8 days, used by an active application
    old_resume = await make_resume(db, student)
    await db.execute(update(Document).where(Document.id == old_resume.id).values(created_at=utcnow() - 8 * DAYS))
    ok_internship = await make_internship(db, owner)
    app_ = await make_application(db, student, ok_internship, resume=old_resume, status="UNDER_REVIEW")
    young_resume = await make_resume(db, student)  # 1. negatives: too young / verified / withdrawn application
    verified = await make_resume(db, student, verification_status="VERIFIED")
    await db.execute(update(Document).where(Document.id == verified.id).values(created_at=utcnow() - 9 * DAYS))
    withdrawn_resume = await make_resume(db, student)
    await db.execute(update(Document).where(Document.id == withdrawn_resume.id).values(created_at=utcnow() - 9 * DAYS))
    other_internship = await make_internship(db, owner)
    await make_application(db, student, other_internship, resume=withdrawn_resume, status="WITHDRAWN")
    await make_application(db, student, await make_internship(db, owner), resume=young_resume)

    # 2. INTERNSHIP_PAST_DEADLINE_OPEN
    expired_open = await make_internship(db, owner, deadline_in_days=-1)
    # 4. UNPAID_LONG_INTERNSHIP (stipend 0, 14 weeks) vs unpaid short vs paid long
    unpaid_long = await make_internship(db, owner, stipend_monthly=0, weeks=14)
    await make_internship(db, owner, stipend_monthly=0, weeks=8)
    await make_internship(db, owner, stipend_monthly=5000, weeks=20)
    # 5. INACTIVE_COMPANY_POSTING: pending + archived companies vs active
    pending_company = await make_company(db, status="PENDING")
    from_pending = await make_internship(db, owner, company=pending_company)
    archived_company = await make_company(db, status="ARCHIVED")
    from_archived = await make_internship(db, owner, company=archived_company, status="PENDING_APPROVAL")
    # 3. INTERVIEW_SHORT_NOTICE: created now, scheduled in 5 h (bypassed rule) vs 48 h notice vs historical interview
    ivs = {}
    for key, delta in (("bad", 5 * HOURS), ("good", 48 * HOURS), ("past", -5 * DAYS)):
        ivs[key] = Interview(
            application_id=app_.id, scheduled_by=owner.id, scheduled_at=utcnow() + delta, mode="PHONE",
            interviewer_name="Panel",
        )
        db.add(ivs[key])
    await db.flush()

    summary = await maintenance.run_compliance_scan(db)
    found = await _violations(db)
    assert found["RESUME_UNVERIFIED_7D"] == {old_resume.id}
    assert found["INTERNSHIP_PAST_DEADLINE_OPEN"] == {expired_open.id}
    assert found["INTERVIEW_SHORT_NOTICE"] == {ivs["bad"].id}
    assert found["UNPAID_LONG_INTERNSHIP"] == {unpaid_long.id}
    assert found["INACTIVE_COMPANY_POSTING"] == {from_pending.id, from_archived.id}
    assert summary["new_violations"] == 7 and summary["policies_checked"] == 5 and summary["open_violations"] == 7
    details = (
        await db.execute(select(PolicyViolation.details).where(PolicyViolation.entity_id == old_resume.id))
    ).scalar_one()
    assert details["application_ids"] == [str(app_.id)]

    # idempotent: second run adds nothing
    again = await maintenance.run_compliance_scan(db)
    assert again["new_violations"] == 0 and again["auto_resolved"] == 0 and again["open_violations"] == 7
    total = (await db.execute(select(PolicyViolation))).scalars().all()
    assert len(total) == 7

    # dismissed stays dismissed; fixed conditions auto-resolve
    await db.execute(
        update(PolicyViolation).where(PolicyViolation.entity_id == unpaid_long.id).values(status="DISMISSED")
    )
    await db.execute(update(Internship).where(Internship.id == expired_open.id).values(status="CLOSED"))
    await db.execute(update(Document).where(Document.id == old_resume.id).values(verification_status="VERIFIED"))
    third = await maintenance.run_compliance_scan(db)
    assert third["auto_resolved"] == 2 and third["new_violations"] == 0
    found = await _violations(db)
    assert "INTERNSHIP_PAST_DEADLINE_OPEN" not in found and "RESUME_UNVERIFIED_7D" not in found
    assert "UNPAID_LONG_INTERNSHIP" not in found  # dismissed, not reopened
    statuses = {
        v.entity_id: v.status for v in (await db.execute(select(PolicyViolation))).scalars()
    }
    assert statuses[unpaid_long.id] == "DISMISSED" and statuses[expired_open.id] == "RESOLVED"


async def test_inactive_policy_is_skipped(db: AsyncSession):
    owner = await make_faculty(db)
    await make_internship(db, owner, deadline_in_days=-1)
    await db.execute(
        update(CompliancePolicy).where(CompliancePolicy.code == "INTERNSHIP_PAST_DEADLINE_OPEN").values(is_active=False)
    )
    summary = await maintenance.run_compliance_scan(db)
    assert "INTERNSHIP_PAST_DEADLINE_OPEN" not in summary["per_policy"] and summary["new_violations"] == 0


# ---- interviews.send_reminders --------------------------------------------------------------------------
async def test_send_reminders_once_within_24h(db: AsyncSession, monkeypatch, captured):
    monkeypatch.setattr(side_effects, "dispatcher", captured)
    student = await make_student(db)
    owner = await make_faculty(db)
    internship = await make_internship(db, owner)

    async def interview(status_: str, hours: float, app_status: str = "INTERVIEW", **kw) -> Interview:
        app_ = await make_application(db, await make_student(db) if kw.pop("other", False) else student,
                                      await make_internship(db, owner), status=app_status)
        iv = Interview(
            application_id=app_.id, scheduled_by=owner.id, scheduled_at=utcnow() + timedelta(hours=hours),
            mode="ONLINE", meeting_link="https://meet.example.com/x", interviewer_name="Panel Lead",
            interviewer_email="panel@example.com", status=status_, **kw,
        )
        db.add(iv)
        await db.flush()
        return iv

    due = await interview("SCHEDULED", 10)
    due_resched = await interview("RESCHEDULED", 23, other=True)
    later = await interview("SCHEDULED", 30, other=True)
    cancelled = await interview("CANCELLED", 5, other=True)
    past = await interview("SCHEDULED", -2, other=True)
    already = await interview("SCHEDULED", 6, other=True, reminder_sent_at=utcnow() - HOURS)

    assert await interviews.send_reminders(db) == 2
    await db.flush()
    await side_effects.flush(db)

    for iv in (due, due_resched, later, cancelled, past, already):
        await db.refresh(iv)
    assert due.reminder_sent_at and due_resched.reminder_sent_at
    assert not later.reminder_sent_at and not cancelled.reminder_sent_at and not past.reminder_sent_at
    assert already.reminder_sent_at is not None

    mails = captured.emails
    assert {e["template"] for e in mails} == {"interview_reminder"}
    student_mail = captured.emails_to(student.email)
    assert len(student_mail) == 1  # student has one due interview ("due"); the other belongs to another student
    ctx = student_mail[0]["context"]
    assert ctx["full_name"] == student.full_name and ctx["meeting_link"] == "https://meet.example.com/x"
    assert ctx["interview_id"] == str(due.id) and ctx["scheduled_at"].endswith("Z")
    assert len(captured.emails_to("panel@example.com")) == 2  # interviewer e-mailed too
    kinds = [n for n in captured.notifications if n["type"] == "INTERVIEW_REMINDER"]
    assert len(kinds) == 2 and {n["user_id"] for n in kinds} >= {student.id}

    # second run: nothing left to remind
    captured.emails.clear()
    assert await interviews.send_reminders(db) == 0
    assert captured.emails == []


# ---- runtime / thin wrappers (real commits through the worker's own NullPool engine) --------------------
def _run_in_thread(coro):
    return asyncio.to_thread(runtime.run_async, coro)


async def test_run_async_uses_private_engine_and_commits():
    email = f"wp4a-{uuid.uuid4().hex[:8]}@campushire.dev"

    async def create() -> uuid.UUID:
        from app.modules.users.models import User

        async with runtime.worker_session() as s:
            u = User(email=email, password_hash="x", role="STUDENT", full_name="Worker Test")
            s.add(u)
            await s.flush()
            return u.id

    async def exists_then_delete(uid: uuid.UUID) -> bool:
        from app.modules.users.models import User

        async with runtime.worker_session() as s:
            found = (await s.get(User, uid)) is not None
            await s.execute(delete(User).where(User.id == uid))
            return found

    uid = await _run_in_thread(create())
    assert await _run_in_thread(exists_then_delete(uid)) is True  # committed, visible from another loop/engine


async def test_worker_session_rolls_back_on_error():
    from app.modules.users.models import User

    email = f"wp4a-{uuid.uuid4().hex[:8]}@campushire.dev"

    async def fail() -> None:
        async with runtime.worker_session() as s:
            s.add(User(email=email, password_hash="x", role="STUDENT", full_name="Rolled Back"))
            await s.flush()
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await _run_in_thread(fail())

    async def count() -> int:
        async with runtime.worker_session() as s:
            return len((await s.execute(select(User).where(User.email == email))).scalars().all())

    assert await _run_in_thread(count()) == 0


async def _commit_job(job_type: str, requested_by=None) -> uuid.UUID:
    async def make() -> uuid.UUID:
        async with runtime.worker_session() as s:
            j = Job(type=job_type, status="QUEUED", requested_by=requested_by, params={})
            s.add(j)
            await s.flush()
            return j.id

    return await _run_in_thread(make())


async def _job_state(job_id: uuid.UUID, delete_after: bool = True) -> tuple[str, str | None]:
    async def read() -> tuple[str, str | None]:
        async with runtime.worker_session() as s:
            j = await s.get(Job, job_id)
            assert j is not None
            out = (j.status, j.error)
            if delete_after:
                await s.delete(j)
            return out

    return await _run_in_thread(read())


@pytest.mark.parametrize(
    ("task_module", "task_name", "target_module", "job_type"),
    [
        (report_tasks, "export_report", "app.modules.reports.service", "REPORT_EXPORT"),
        (data_tasks, "export_data", "app.modules.admin.exporter", "DATA_EXPORT"),
        (data_tasks, "import_data", "app.modules.admin.importer", "DATA_IMPORT"),
    ],
)
async def test_thin_wrappers_call_sibling_async_functions(monkeypatch, task_module, task_name, target_module, job_type):
    calls: list[object] = []

    async def fake_run(job_id: uuid.UUID) -> None:
        calls.append(job_id)

    fake = types.ModuleType(target_module)
    fake.run_export_job = fake_run  # type: ignore[attr-defined]
    fake.run_import_job = fake_run  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, target_module, fake)
    jid = uuid.uuid4()
    await asyncio.to_thread(getattr(task_module, task_name), str(jid))
    assert calls == [jid]  # delivered as a uuid.UUID (the callee is annotated with UUID)


async def test_wrapper_marks_job_failed_when_callee_raises(monkeypatch):
    job_id = await _commit_job("REPORT_EXPORT")

    async def broken(job_id: uuid.UUID) -> None:
        raise ValueError("render exploded")

    fake = types.ModuleType("app.modules.reports.service")
    fake.run_export_job = broken  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "app.modules.reports.service", fake)
    with pytest.raises(ValueError):
        await asyncio.to_thread(report_tasks.export_report, str(job_id))
    status, error = await _job_state(job_id)
    assert status == "FAILED" and "render exploded" in (error or "")


async def test_call_job_function_passes_str_when_annotated_str():
    seen = []

    async def takes_str(job_id: str) -> None:
        seen.append(job_id)

    jid = str(uuid.uuid4())
    await runtime.call_job_function(takes_str, jid)
    assert seen == [jid]


async def test_compliance_scan_task_tracks_job_row():
    job_id = await _commit_job("COMPLIANCE_SCAN")
    summary = await _run_in_thread(maintenance.compliance_scan_job(job_id))
    assert summary["policies_checked"] == 5
    status, error = await _job_state(job_id)
    assert status == "SUCCEEDED" and error is None

    # beat calls without job_id: the task creates its own tracking row
    await _run_in_thread(maintenance.compliance_scan_job(None))

    async def cleanup() -> int:
        async with runtime.worker_session() as s:
            rows = (await s.execute(select(Job).where(Job.type == "COMPLIANCE_SCAN"))).scalars().all()
            assert len(rows) == 1 and rows[0].status == "SUCCEEDED" and rows[0].requested_by is None
            await s.execute(delete(Job).where(Job.id == rows[0].id))
            return len(rows)

    assert await _run_in_thread(cleanup()) == 1
