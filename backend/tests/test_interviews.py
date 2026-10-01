from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update

from app.modules.admin.models import AuditLog
from app.modules.applications.models import ApplicationStatusHistory
from app.modules.interviews.models import Interview
from tests.factories import (
    auth_headers,
    make_admin,
    make_application,
    make_company_user,
    make_faculty,
    make_internship,
    make_student,
)

URL = "/api/v1/interviews"


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def body(application, when, **over):
    data = {
        "application_id": str(application.id),
        "scheduled_at": iso(when),
        "duration_minutes": 30,
        "mode": "ONLINE",
        "meeting_link": "https://meet.example.com/abc",
        "interviewer_name": "Dr. Interviewer",
    }
    data.update(over)
    return data


def in_days(d: float) -> datetime:
    return datetime.now(UTC) + timedelta(days=d)


async def world(db, *, deadline_in_days=20, status="SHORTLISTED"):
    faculty = await make_faculty(db)
    student = await make_student(db)
    internship = await make_internship(db, faculty, deadline_in_days=deadline_in_days)
    application = await make_application(db, student, internship, status=status)
    return faculty, student, internship, application


async def schedule(client, faculty, application, when=None, **over):
    r = await client.post(URL, headers=auth_headers(faculty), json=body(application, when or in_days(3), **over))
    assert r.status_code == 201, r.text
    return r.json()


# ---- create -----------------------------------------------------------------------------------------------------


async def test_create_moves_application_to_interview_and_notifies(client, db, captured):
    faculty, student, internship, application = await world(db)
    data = await schedule(client, faculty, application, interviewer_email="Panel@Example.com")
    assert data["status"] == "SCHEDULED" and data["result"] == "PENDING" and data["reschedule_count"] == 0
    assert data["student"]["id"] == str(student.id)
    assert data["internship"]["id"] == str(internship.id)
    assert data["interviewer_email"] == "panel@example.com"
    assert "comments" in data  # staff payload includes the internal field

    await db.refresh(application)
    assert application.status == "INTERVIEW"
    hist = (
        await db.execute(
            select(ApplicationStatusHistory.to_status).where(ApplicationStatusHistory.application_id == application.id)
        )
    ).scalars().all()
    assert "INTERVIEW" in hist
    assert [e["template"] for e in captured.emails_to(student.email)].count("interview_scheduled") == 1
    assert any(n["type"] == "INTERVIEW_SCHEDULED" and n["user_id"] == student.id for n in captured.notifications)
    audits = (await db.execute(select(func.count()).select_from(AuditLog).where(AuditLog.action == "interview.create"))).scalar_one()
    assert audits == 1


async def test_create_second_interview_keeps_interview_status(client, db):
    faculty, _s, _i, application = await world(db)
    await schedule(client, faculty, application, in_days(3))
    await schedule(client, faculty, application, in_days(4))
    await db.refresh(application)
    assert application.status == "INTERVIEW"


async def test_notice_23h59m_422(client, db):
    faculty, _s, _i, application = await world(db)
    when = datetime.now(UTC) + timedelta(hours=23, minutes=59)
    r = await client.post(URL, headers=auth_headers(faculty), json=body(application, when))
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INTERVIEW_NOTICE_TOO_SHORT"


async def test_notice_24h01m_ok(client, db):
    faculty, _s, _i, application = await world(db)
    when = datetime.now(UTC) + timedelta(hours=24, minutes=1)
    r = await client.post(URL, headers=auth_headers(faculty), json=body(application, when))
    assert r.status_code == 201, r.text


async def test_after_deadline_422(client, db):
    faculty, _s, _i, application = await world(db, deadline_in_days=2)
    r = await client.post(URL, headers=auth_headers(faculty), json=body(application, in_days(3)))
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INTERVIEW_AFTER_DEADLINE"


async def test_must_end_before_deadline(client, db):
    faculty, _s, internship, application = await world(db, deadline_in_days=3)
    # starts 10 minutes before the deadline but a 30 minute interview ends after it
    when = internship.application_deadline - timedelta(minutes=10)
    r = await client.post(URL, headers=auth_headers(faculty), json=body(application, when))
    assert r.status_code == 422 and r.json()["error"]["code"] == "INTERVIEW_AFTER_DEADLINE"
    ok = internship.application_deadline - timedelta(minutes=30)
    r = await client.post(URL, headers=auth_headers(faculty), json=body(application, ok))
    assert r.status_code == 201, r.text


@pytest.mark.parametrize("status", ["PENDING", "UNDER_REVIEW", "ACCEPTED", "REJECTED", "WITHDRAWN"])
async def test_requires_shortlisted(client, db, status):
    faculty, _s, _i, application = await world(db, status=status)
    r = await client.post(URL, headers=auth_headers(faculty), json=body(application, in_days(3)))
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


async def test_overlap_conflict_409(client, db):
    faculty = await make_faculty(db)
    student = await make_student(db)
    a1 = await make_application(db, student, await make_internship(db, faculty), status="SHORTLISTED")
    a2 = await make_application(db, student, await make_internship(db, faculty), status="SHORTLISTED")
    start = in_days(3)
    await schedule(client, faculty, a1, start)
    r = await client.post(URL, headers=auth_headers(faculty), json=body(a2, start + timedelta(minutes=15)))
    assert r.status_code == 409 and r.json()["error"]["code"] == "INTERVIEW_CONFLICT"
    # back-to-back is fine
    r = await client.post(URL, headers=auth_headers(faculty), json=body(a2, start + timedelta(minutes=30)))
    assert r.status_code == 201, r.text


async def test_cancelled_interview_does_not_conflict(client, db):
    faculty = await make_faculty(db)
    student = await make_student(db)
    a1 = await make_application(db, student, await make_internship(db, faculty), status="SHORTLISTED")
    a2 = await make_application(db, student, await make_internship(db, faculty), status="SHORTLISTED")
    start = in_days(3)
    first = await schedule(client, faculty, a1, start)
    assert (await client.post(f"{URL}/{first['id']}/cancel", headers=auth_headers(faculty), json={"reason": "x"})).status_code == 200
    await schedule(client, faculty, a2, start)


async def test_online_requires_meeting_link_and_onsite_requires_location(client, db):
    faculty, _s, _i, application = await world(db)
    h = auth_headers(faculty)
    r = await client.post(URL, headers=h, json=body(application, in_days(3), meeting_link=None))
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    r = await client.post(URL, headers=h, json=body(application, in_days(3), mode="ONSITE", meeting_link=None))
    assert r.status_code == 422
    r = await client.post(URL, headers=h, json=body(application, in_days(3), mode="ONSITE", meeting_link=None, location="HQ, Room 4"))
    assert r.status_code == 201, r.text
    r = await client.post(URL, headers=h, json=body(application, in_days(4), mode="PHONE", meeting_link=None))
    assert r.status_code == 201, r.text


async def test_duration_bounds(client, db):
    faculty, _s, _i, application = await world(db)
    h = auth_headers(faculty)
    assert (await client.post(URL, headers=h, json=body(application, in_days(3), duration_minutes=14))).status_code == 422
    assert (await client.post(URL, headers=h, json=body(application, in_days(3), duration_minutes=241))).status_code == 422


async def test_create_permissions(client, db):
    faculty, student, _i, application = await world(db)
    other_faculty = await make_faculty(db)
    other_company_user = await make_company_user(db)
    assert (await client.post(URL, headers=auth_headers(student), json=body(application, in_days(3)))).status_code == 403
    assert (await client.post(URL, json=body(application, in_days(3)))).status_code == 401
    r = await client.post(URL, headers=auth_headers(other_faculty), json=body(application, in_days(3)))
    assert r.status_code == 404
    r = await client.post(URL, headers=auth_headers(other_company_user), json=body(application, in_days(3)))
    assert r.status_code == 404
    admin = await make_admin(db)
    assert (await client.post(URL, headers=auth_headers(admin), json=body(application, in_days(3)))).status_code == 201


async def test_company_member_can_schedule_for_company_internship(client, db):
    cu = await make_company_user(db)
    internship = await make_internship(db, cu, company=cu.company)
    student = await make_student(db)
    application = await make_application(db, student, internship, status="SHORTLISTED")
    r = await client.post(URL, headers=auth_headers(cu), json=body(application, in_days(3)))
    assert r.status_code == 201, r.text


async def test_unknown_interviewer_user_422(client, db):
    faculty, _s, _i, application = await world(db)
    student2 = await make_student(db)
    r = await client.post(
        URL, headers=auth_headers(faculty), json=body(application, in_days(3), interviewer_user_id=str(student2.id))
    )
    assert r.status_code == 422


# ---- reschedule -------------------------------------------------------------------------------------------------


async def test_reschedule_ok(client, db, captured):
    faculty, student, _i, application = await world(db)
    iv = await schedule(client, faculty, application, in_days(3))
    new_when = in_days(5)
    r = await client.patch(
        f"{URL}/{iv['id']}/reschedule",
        headers=auth_headers(faculty),
        json={"scheduled_at": iso(new_when), "duration_minutes": 45, "reason": "Panel unavailable"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "RESCHEDULED" and data["reschedule_count"] == 1 and data["duration_minutes"] == 45
    assert len(captured.emails_to(student.email, "interview_rescheduled")) == 1
    # rescheduling onto its own old slot window must not conflict with itself
    r = await client.patch(
        f"{URL}/{iv['id']}/reschedule",
        headers=auth_headers(faculty),
        json={"scheduled_at": iso(new_when + timedelta(minutes=10)), "reason": "Shift"},
    )
    assert r.status_code == 200 and r.json()["reschedule_count"] == 2


async def test_reschedule_enforces_rules(client, db):
    faculty, _s, internship, application = await world(db, deadline_in_days=10)
    iv = await schedule(client, faculty, application, in_days(3))
    h = auth_headers(faculty)
    url = f"{URL}/{iv['id']}/reschedule"
    r = await client.patch(url, headers=h, json={"scheduled_at": iso(datetime.now(UTC) + timedelta(hours=23)), "reason": "x"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INTERVIEW_NOTICE_TOO_SHORT"
    r = await client.patch(url, headers=h, json={"scheduled_at": iso(in_days(11)), "reason": "x"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INTERVIEW_AFTER_DEADLINE"


async def test_reschedule_overlap_conflict(client, db):
    faculty = await make_faculty(db)
    student = await make_student(db)
    a1 = await make_application(db, student, await make_internship(db, faculty), status="SHORTLISTED")
    a2 = await make_application(db, student, await make_internship(db, faculty), status="SHORTLISTED")
    first = await schedule(client, faculty, a1, in_days(3))
    await schedule(client, faculty, a2, in_days(4))
    r = await client.patch(
        f"{URL}/{first['id']}/reschedule",
        headers=auth_headers(faculty),
        json={"scheduled_at": iso(in_days(4)), "reason": "x"},
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "INTERVIEW_CONFLICT"


async def test_reschedule_cancelled_409_and_requires_reason(client, db):
    faculty, _s, _i, application = await world(db)
    iv = await schedule(client, faculty, application, in_days(3))
    h = auth_headers(faculty)
    r = await client.patch(f"{URL}/{iv['id']}/reschedule", headers=h, json={"scheduled_at": iso(in_days(4))})
    assert r.status_code == 422
    await client.post(f"{URL}/{iv['id']}/cancel", headers=h, json={"reason": "gone"})
    r = await client.patch(f"{URL}/{iv['id']}/reschedule", headers=h, json={"scheduled_at": iso(in_days(4)), "reason": "x"})
    assert r.status_code == 409


# ---- cancel -----------------------------------------------------------------------------------------------------


async def test_cancel_last_interview_back_to_shortlisted(client, db, captured):
    faculty, student, _i, application = await world(db)
    first = await schedule(client, faculty, application, in_days(3))
    second = await schedule(client, faculty, application, in_days(4))
    h = auth_headers(faculty)
    r = await client.post(f"{URL}/{first['id']}/cancel", headers=h, json={"reason": "Interviewer sick"})
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED" and r.json()["cancel_reason"] == "Interviewer sick"
    await db.refresh(application)
    assert application.status == "INTERVIEW"  # another one is still active
    r = await client.post(f"{URL}/{second['id']}/cancel", headers=h, json={"reason": "No longer needed"})
    assert r.status_code == 200
    await db.refresh(application)
    assert application.status == "SHORTLISTED"
    assert len(captured.emails_to(student.email, "interview_cancelled")) == 2
    # cancelling twice conflicts
    assert (await client.post(f"{URL}/{second['id']}/cancel", headers=h, json={"reason": "again"})).status_code == 409


async def test_delete_is_cancel_alias(client, db):
    faculty, _s, _i, application = await world(db)
    iv = await schedule(client, faculty, application, in_days(3))
    r = await client.delete(f"{URL}/{iv['id']}", headers=auth_headers(faculty))
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    await db.refresh(application)
    assert application.status == "SHORTLISTED"


async def test_cancel_permissions(client, db):
    faculty, student, _i, application = await world(db)
    iv = await schedule(client, faculty, application, in_days(3))
    assert (await client.post(f"{URL}/{iv['id']}/cancel", headers=auth_headers(student), json={"reason": "x"})).status_code == 403
    other = await make_faculty(db)
    assert (await client.post(f"{URL}/{iv['id']}/cancel", headers=auth_headers(other), json={"reason": "x"})).status_code == 404


# ---- result -----------------------------------------------------------------------------------------------------


async def _make_past(db, interview_id):
    await db.execute(
        update(Interview).where(Interview.id == interview_id).values(scheduled_at=datetime.now(UTC) - timedelta(hours=2))
    )
    await db.flush()


async def test_result_only_after_scheduled_time(client, db):
    faculty, _s, _i, application = await world(db)
    iv = await schedule(client, faculty, application, in_days(3))
    payload = {"status": "COMPLETED", "result": "PASS", "score": 4, "comments": "internal", "feedback_for_student": "Well done"}
    r = await client.patch(f"{URL}/{iv['id']}/result", headers=auth_headers(faculty), json=payload)
    assert r.status_code == 409
    admin = await make_admin(db)
    r = await client.patch(f"{URL}/{iv['id']}/result", headers=auth_headers(admin), json=payload)
    assert r.status_code == 200, r.text  # admin bypass


async def test_result_flow_and_student_visibility(client, db):
    faculty, student, _i, application = await world(db)
    iv = await schedule(client, faculty, application, in_days(3))
    await _make_past(db, iv["id"])
    payload = {"status": "COMPLETED", "result": "PASS", "score": 5, "comments": "internal note", "feedback_for_student": "Great"}
    r = await client.patch(f"{URL}/{iv['id']}/result", headers=auth_headers(faculty), json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "COMPLETED" and data["result"] == "PASS" and data["score"] == 5
    assert data["comments"] == "internal note"

    r = await client.get(f"{URL}/{iv['id']}", headers=auth_headers(student))
    assert r.status_code == 200
    sdata = r.json()
    assert "comments" not in sdata
    assert sdata["feedback_for_student"] == "Great"
    lst = await client.get(URL, headers=auth_headers(student))
    assert all("comments" not in item for item in lst.json()["items"])
    # completed interviews cannot be completed again
    r = await client.patch(f"{URL}/{iv['id']}/result", headers=auth_headers(faculty), json=payload)
    assert r.status_code == 409


async def test_result_validation_and_no_show(client, db):
    faculty, _s, _i, application = await world(db)
    iv = await schedule(client, faculty, application, in_days(3))
    await _make_past(db, iv["id"])
    h = auth_headers(faculty)
    url = f"{URL}/{iv['id']}/result"
    assert (await client.patch(url, headers=h, json={"status": "CANCELLED", "result": "PASS"})).status_code == 422
    assert (await client.patch(url, headers=h, json={"status": "COMPLETED", "result": "PASS", "score": 6})).status_code == 422
    assert (await client.patch(url, headers=h, json={"status": "COMPLETED", "result": "PASS", "score": 0})).status_code == 422
    r = await client.patch(url, headers=h, json={"status": "NO_SHOW", "result": "FAIL"})
    assert r.status_code == 200 and r.json()["status"] == "NO_SHOW"


async def test_student_does_not_see_feedback_before_completion(client, db):
    faculty, student, _i, application = await world(db)
    iv = await schedule(client, faculty, application, in_days(3))
    await db.execute(update(Interview).where(Interview.id == iv["id"]).values(feedback_for_student="early"))
    await db.flush()
    r = await client.get(f"{URL}/{iv['id']}", headers=auth_headers(student))
    assert r.json()["feedback_for_student"] is None


async def test_interviewer_user_can_record_result(client, db):
    faculty, _s, _i, application = await world(db)
    panel = await make_faculty(db)
    iv = await schedule(client, faculty, application, in_days(3), interviewer_user_id=str(panel.id))
    await _make_past(db, iv["id"])
    # the interviewer sees it and records the result although they do not own the internship
    assert (await client.get(f"{URL}/{iv['id']}", headers=auth_headers(panel))).status_code == 200
    r = await client.patch(
        f"{URL}/{iv['id']}/result", headers=auth_headers(panel), json={"status": "COMPLETED", "result": "ON_HOLD"}
    )
    assert r.status_code == 200 and r.json()["result"] == "ON_HOLD"
    # but cannot reschedule
    r = await client.patch(
        f"{URL}/{iv['id']}/reschedule", headers=auth_headers(panel), json={"scheduled_at": iso(in_days(6)), "reason": "x"}
    )
    assert r.status_code in (403, 409)


# ---- reads / scoping --------------------------------------------------------------------------------------------


async def test_list_scoping_and_filters(client, db):
    faculty, student, _i, application = await world(db)
    other_faculty = await make_faculty(db)
    other_student = await make_student(db)
    other_app = await make_application(
        db, other_student, await make_internship(db, other_faculty), status="SHORTLISTED"
    )
    mine = await schedule(client, faculty, application, in_days(3))
    theirs = await schedule(client, other_faculty, other_app, in_days(3))
    admin = await make_admin(db)

    def ids(resp):
        return {i["id"] for i in resp.json()["items"]}

    assert ids(await client.get(URL, headers=auth_headers(faculty))) == {mine["id"]}
    assert ids(await client.get(URL, headers=auth_headers(student))) == {mine["id"]}
    assert ids(await client.get(URL, headers=auth_headers(other_student))) == {theirs["id"]}
    assert ids(await client.get(URL, headers=auth_headers(admin))) == {mine["id"], theirs["id"]}
    assert (await client.get(f"{URL}/{theirs['id']}", headers=auth_headers(faculty))).status_code == 404
    assert (await client.get(f"{URL}/{theirs['id']}", headers=auth_headers(student))).status_code == 404
    assert (await client.get(URL)).status_code == 401

    h = auth_headers(admin)
    r = await client.get(URL, headers=h, params={"status": "CANCELLED"})
    assert r.json()["total"] == 0
    r = await client.get(URL, headers=h, params={"application_id": str(application.id)})
    assert ids(r) == {mine["id"]}
    r = await client.get(URL, headers=h, params={"from": iso(in_days(2)), "to": iso(in_days(4))})
    assert r.json()["total"] == 2
    r = await client.get(URL, headers=h, params={"from": iso(in_days(5))})
    assert r.json()["total"] == 0
    body_ = (await client.get(URL, headers=h)).json()
    assert {"items", "total", "page", "page_size", "pages"} <= set(body_)
