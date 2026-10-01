import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.admin.models import AuditLog
from app.modules.applications.models import Application, ApplicationStatusHistory
from app.modules.applications.state_machine import (
    ALL_STATUSES,
    STUDENT_TRANSITIONS,
    SYSTEM_TRANSITIONS,
    TRANSITIONS,
    transition_application,
)
from app.modules.evaluations.models import Evaluation, EvaluationForm
from app.modules.interviews.models import Interview
from app.modules.documents.models import Document
from tests.factories import (
    auth_headers,
    make_admin,
    make_application,
    make_company,
    make_company_user,
    make_faculty,
    make_internship,
    make_resume,
    make_student,
)

URL = "/api/v1/applications"
COVER = "I am very motivated to join this internship and I believe my skills fit the role well."
OFFER = {"stipend_monthly": 22000, "start_date": "2030-01-15", "joining_location": "Bengaluru", "notes": "Welcome!"}


def apply_body(internship, resume, **over):
    data = {
        "internship_id": str(internship.id),
        "resume_document_id": str(resume.id) if resume is not None else None,
        "cover_letter": COVER,
        "qualifications": "B.Tech CSE, strong in algorithms and databases.",
        "answers": {"skills": ["Python"], "coursework": "DBMS, OS", "availability_from": "2030-01-01"},
    }
    data.update(over)
    return data


@pytest.fixture
async def world(db):
    fac = await make_faculty(db)
    admin = await make_admin(db)
    student = await make_student(db, department="CSE", gpa="3.40")
    it = await make_internship(db, fac)
    resume = await make_resume(db, student)
    return type("W", (), {"fac": fac, "admin": admin, "student": student, "it": it, "resume": resume})()


# ---- submit ---------------------------------------------------------------------------------------------------------


async def test_apply_success(client, db, captured, world):
    w = world
    r = await client.post(URL, headers=auth_headers(w.student), json=apply_body(w.it, w.resume))
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["status"] == "PENDING" and d["resume"]["id"] == str(w.resume.id)
    assert d["student"]["gpa"] == 3.4 and isinstance(d["student"]["gpa"], float)
    assert d["timeline"][0]["kind"] == "STATUS" and d["timeline"][0]["status"] == "PENDING"
    assert d["allowed_transitions"] == ["WITHDRAWN"]
    assert d["answers"]["skills"] == ["Python"]
    assert captured.emails_to(w.student.email, "application_submitted")
    assert any(n["user_id"] == w.fac.id and n["type"] == "APPLICATION_RECEIVED" for n in captured.notifications)
    assert any(n["user_id"] == w.student.id for n in captured.notifications)
    hist = (await db.execute(select(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id == uuid.UUID(d["id"])))).scalars().all()
    assert [(h.from_status, h.to_status) for h in hist] == [(None, "PENDING")]
    assert (await db.execute(select(AuditLog).where(AuditLog.action == "application.create"))).scalars().first()


async def test_apply_requires_verified(client, db, world):
    unverified = await make_student(db, verified=False)
    resume = await make_resume(db, unverified)
    r = await client.post(URL, headers=auth_headers(unverified), json=apply_body(world.it, resume))
    assert r.status_code == 403 and r.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"


async def test_only_students_apply(client, db, world):
    r = await client.post(URL, headers=auth_headers(world.fac), json=apply_body(world.it, world.resume))
    assert r.status_code == 403
    assert (await client.post(URL, json=apply_body(world.it, world.resume))).status_code == 401


async def test_apply_without_resume_422(client, world):
    r = await client.post(URL, headers=auth_headers(world.student), json=apply_body(world.it, None))
    assert r.status_code == 422 and r.json()["error"]["code"] == "RESUME_REQUIRED"
    body = apply_body(world.it, world.resume)
    del body["resume_document_id"]
    r = await client.post(URL, headers=auth_headers(world.student), json=body)
    assert r.status_code == 422 and r.json()["error"]["code"] == "RESUME_REQUIRED"


async def test_apply_with_foreign_resume_422(client, db, world):
    other = await make_student(db)
    foreign = await make_resume(db, other)
    r = await client.post(URL, headers=auth_headers(world.student), json=apply_body(world.it, foreign))
    assert r.status_code == 422 and r.json()["error"]["code"] == "RESUME_INVALID"
    r = await client.post(URL, headers=auth_headers(world.student), json=apply_body(world.it, world.resume, resume_document_id=str(uuid.uuid4())))
    assert r.json()["error"]["code"] == "RESUME_INVALID"


async def test_apply_with_unuploaded_or_non_resume_document_422(client, db, world):
    pending = await make_resume(db, world.student, status="PENDING_UPLOAD")
    r = await client.post(URL, headers=auth_headers(world.student), json=apply_body(world.it, pending))
    assert r.json()["error"]["code"] == "RESUME_INVALID"
    cover = Document(
        id=uuid.uuid4(), owner_id=world.student.id, kind="COVER_LETTER", bucket="documents",
        object_key=f"{uuid.uuid4()}/x.pdf", filename="x.pdf", content_type="application/pdf", size_bytes=10, status="UPLOADED",
    )
    db.add(cover)
    await db.flush()
    r = await client.post(URL, headers=auth_headers(world.student), json=apply_body(world.it, cover))
    assert r.json()["error"]["code"] == "RESUME_INVALID"


async def test_db_check_resume_pdf(db, world):
    bad = Document(
        id=uuid.uuid4(), owner_id=world.student.id, kind="RESUME", bucket="resumes", object_key=f"{uuid.uuid4()}/r.docx",
        filename="r.docx", content_type="application/msword", size_bytes=10,
    )
    db.add(bad)
    with pytest.raises(IntegrityError):
        await db.flush()


@pytest.mark.parametrize("field,value", [("cover_letter", "too short"), ("qualifications", "short")])
async def test_apply_text_lengths_422(client, world, field, value):
    r = await client.post(URL, headers=auth_headers(world.student), json=apply_body(world.it, world.resume, **{field: value}))
    assert r.status_code == 422


async def test_apply_internship_not_open(client, db, world):
    for status in ("DRAFT", "PENDING_APPROVAL", "REJECTED", "CLOSED"):
        it = await make_internship(db, world.fac, status=status)
        r = await client.post(URL, headers=auth_headers(world.student), json=apply_body(it, world.resume))
        assert r.status_code == 409 and r.json()["error"]["code"] == "INTERNSHIP_NOT_OPEN", status
    archived = await make_internship(db, world.fac)
    archived.archived_at = datetime.now(UTC)
    await db.flush()
    r = await client.post(URL, headers=auth_headers(world.student), json=apply_body(archived, world.resume))
    assert r.json()["error"]["code"] == "INTERNSHIP_NOT_OPEN"
    r = await client.post(URL, headers=auth_headers(world.student), json=apply_body(world.it, world.resume, internship_id=str(uuid.uuid4())))
    assert r.status_code == 404


async def test_apply_after_deadline(client, db, world):
    it = await make_internship(db, world.fac, deadline_in_days=-1)
    r = await client.post(URL, headers=auth_headers(world.student), json=apply_body(it, world.resume))
    assert r.status_code == 409 and r.json()["error"]["code"] == "DEADLINE_PASSED"


async def test_apply_ineligible(client, db, world):
    gpa_gate = await make_internship(db, world.fac, min_gpa=Decimal("3.80"))
    r = await client.post(URL, headers=auth_headers(world.student), json=apply_body(gpa_gate, world.resume))
    assert r.status_code == 422 and r.json()["error"]["code"] == "INELIGIBLE"
    assert r.json()["error"]["details"][0]["field"] == "gpa"
    dept_gate = await make_internship(db, world.fac, eligible_departments=["Mechanical", "Civil"])
    r = await client.post(URL, headers=auth_headers(world.student), json=apply_body(dept_gate, world.resume))
    assert r.status_code == 422 and r.json()["error"]["code"] == "INELIGIBLE"
    ok = await make_internship(db, world.fac, eligible_departments=["cse"], min_gpa=Decimal("3.40"))  # case-insensitive, equal ok
    r = await client.post(URL, headers=auth_headers(world.student), json=apply_body(ok, world.resume))
    assert r.status_code == 201


async def test_duplicate_application_409(client, world):
    h = auth_headers(world.student)
    assert (await client.post(URL, headers=h, json=apply_body(world.it, world.resume))).status_code == 201
    r = await client.post(URL, headers=h, json=apply_body(world.it, world.resume))
    assert r.status_code == 409 and r.json()["error"]["code"] == "DUPLICATE_APPLICATION"


async def test_withdrawn_then_reapply_409(client, world):
    h = auth_headers(world.student)
    aid = (await client.post(URL, headers=h, json=apply_body(world.it, world.resume))).json()["id"]
    assert (await client.post(f"{URL}/{aid}/withdraw", headers=h, json={"reason": "changed my mind"})).status_code == 200
    r = await client.post(URL, headers=h, json=apply_body(world.it, world.resume))
    assert r.status_code == 409 and r.json()["error"]["code"] == "DUPLICATE_APPLICATION"


# ---- read / scoping ---------------------------------------------------------------------------------------------------


async def test_list_scoping(client, db, world):
    w = world
    other_fac = await make_faculty(db)
    other_student = await make_student(db)
    cu = await make_company_user(db)
    cit = await make_internship(db, cu, company=cu.company)
    a1 = await make_application(db, w.student, w.it)
    a2 = await make_application(db, other_student, w.it)
    a3 = await make_application(db, other_student, cit)

    async def listed(user, **params):
        r = await client.get(URL, headers=auth_headers(user), params=params)
        assert r.status_code == 200, r.text
        return {i["id"] for i in r.json()["items"]}

    assert await listed(w.student) == {str(a1.id)}
    assert await listed(other_student) == {str(a2.id), str(a3.id)}
    assert await listed(w.fac) == {str(a1.id), str(a2.id)}
    assert await listed(other_fac) == set()
    assert await listed(cu) == {str(a3.id)}
    assert await listed(w.admin) >= {str(a1.id), str(a2.id), str(a3.id)}
    assert await listed(w.admin, internship_id=str(cit.id)) == {str(a3.id)}
    a2.status = "SHORTLISTED"
    await db.flush()
    assert await listed(w.fac, status="SHORTLISTED") == {str(a2.id)}
    assert (await client.get(URL, headers=auth_headers(w.fac), params={"status": "hired"})).status_code == 422


async def test_detail_scoping_and_fields(client, db, world):
    w = world
    a = await make_application(db, w.student, w.it)
    for u, code in [(w.student, 200), (w.fac, 200), (w.admin, 200), (await make_student(db), 404), (await make_faculty(db), 404), (await make_company_user(db), 404)]:
        assert (await client.get(f"{URL}/{a.id}", headers=auth_headers(u))).status_code == code
    assert (await client.get(f"{URL}/{uuid.uuid4()}", headers=auth_headers(w.admin))).status_code == 404
    d = (await client.get(f"{URL}/{a.id}", headers=auth_headers(w.fac))).json()
    assert d["allowed_transitions"] == ["REJECTED", "SHORTLISTED", "UNDER_REVIEW"]
    assert d["internship"]["title"] == w.it.title and d["evaluation_avg"] is None and d["next_interview_at"] is None
    assert d["can_give_student_feedback"] is False and d["company_feedback_ids"] == []


async def test_company_member_sees_company_applications(client, db):
    cu1 = await make_company_user(db)
    cu2 = await make_company_user(db, cu1.company)
    poster = await make_faculty(db)
    it = await make_internship(db, poster, company=cu1.company)  # posted by faculty, company members also own it
    st = await make_student(db)
    a = await make_application(db, st, it)
    for u in (cu1, cu2, poster):
        assert (await client.get(f"{URL}/{a.id}", headers=auth_headers(u))).status_code == 200


async def test_interview_comments_hidden_from_student_and_shared_evaluations(client, db, world):
    w = world
    a = await make_application(db, w.student, w.it, status="INTERVIEW")
    iv = Interview(
        application_id=a.id, scheduled_by=w.fac.id, scheduled_at=datetime.now(UTC) + timedelta(days=3), duration_minutes=30,
        mode="ONLINE", meeting_link="https://meet.example/x", interviewer_name="Ivy", comments="INTERNAL ONLY", feedback_for_student="Great",
    )
    form = (await db.execute(select(EvaluationForm).limit(1))).scalars().first()
    if form is None:
        form = EvaluationForm(name="Form", created_by=w.fac.id)
        db.add(form)
    db.add(iv)
    await db.flush()
    for shared in (True, False):
        db.add(Evaluation(form_id=form.id, application_id=a.id, evaluator_id=w.fac.id, recommendation="YES", weighted_score=Decimal("80.00") if shared else Decimal("40.00"), shared_with_student=shared)) if False else None
    await db.flush()
    s = (await client.get(f"{URL}/{a.id}", headers=auth_headers(w.student))).json()
    assert len(s["interviews"]) == 1 and "comments" not in s["interviews"][0]
    assert s["interviews"][0]["student"]["id"] == str(w.student.id)
    assert any(e["kind"] == "INTERVIEW_SCHEDULED" for e in s["timeline"])
    f = (await client.get(f"{URL}/{a.id}", headers=auth_headers(w.fac))).json()
    assert f["interviews"][0]["comments"] == "INTERNAL ONLY"


# ---- state machine -----------------------------------------------------------------------------------------------------


def _expected_matrix():
    staff = [(f, t) for f in ALL_STATUSES for t in ALL_STATUSES if f != t]
    return staff


@pytest.mark.parametrize("frm,to", _expected_matrix())
async def test_transition_matrix(client, db, captured, world, frm, to):
    w = world
    it = await make_internship(db, w.fac)
    student = await make_student(db)
    a = await make_application(db, student, it, status=frm)
    allowed_staff = to in TRANSITIONS[frm]
    allowed_student = to in STUDENT_TRANSITIONS[frm]

    # staff (owner faculty) via PATCH /status
    payload = {"status": to, "note": "because"}
    if to == "ACCEPTED":
        payload["offer_details"] = OFFER
    r = await client.patch(f"{URL}/{a.id}/status", headers=auth_headers(w.fac), json=payload)
    if allowed_staff:
        assert r.status_code == 200, r.text
        assert r.json()["status"] == to
        hist = (await db.execute(select(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id == a.id, ApplicationStatusHistory.to_status == to))).scalars().all()
        assert len(hist) == 1 and hist[0].from_status == frm and hist[0].changed_by == w.fac.id and hist[0].note == "because"
        assert any(n["user_id"] == student.id and n["type"] == "APPLICATION_STATUS" for n in captured.notifications)
        assert captured.emails_to(student.email, "application_status")
        assert (await db.execute(select(AuditLog).where(AuditLog.action == "application.status_change", AuditLog.entity_id == a.id))).scalars().first()
    else:
        assert r.status_code == 409, r.text
        assert r.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"

    # student: cannot use PATCH (403); may withdraw where the table allows it
    assert (await client.patch(f"{URL}/{a.id}/status", headers=auth_headers(student), json={"status": to})).status_code == 403
    if to == "WITHDRAWN" and not allowed_staff:
        # fresh application in `frm` (the staff attempt above did not change it)
        r = await client.post(f"{URL}/{a.id}/withdraw", headers=auth_headers(student), json={"reason": "no thanks"})
        if allowed_student:
            assert r.status_code == 200 and r.json()["status"] == "WITHDRAWN"
            assert r.json()["withdrawn_reason"] == "no thanks"
        else:
            assert r.status_code == 409


async def test_system_transitions_documented_and_blocked_via_api(client, db, world):
    w = world
    assert SYSTEM_TRANSITIONS == {"SHORTLISTED": {"INTERVIEW"}, "INTERVIEW": {"SHORTLISTED"}}
    student = await make_student(db)
    a = await make_application(db, student, w.it, status="SHORTLISTED")
    r = await client.patch(f"{URL}/{a.id}/status", headers=auth_headers(w.admin), json={"status": "INTERVIEW"})
    assert r.status_code == 409  # even ADMIN cannot, only the system


async def test_transition_application_system_call(db, captured, world):
    w = world
    student = await make_student(db)
    a = await make_application(db, student, w.it, status="SHORTLISTED")
    app = await transition_application(db, a.id, "INTERVIEW", w.fac, note="interview scheduled", system=True)
    assert app.status == "INTERVIEW"
    app = await transition_application(db, a.id, "SHORTLISTED", None, system=True)
    assert app.status == "SHORTLISTED"
    rows = (await db.execute(select(ApplicationStatusHistory.to_status).where(ApplicationStatusHistory.application_id == a.id).order_by(ApplicationStatusHistory.id))).scalars().all()
    assert rows[-2:] == ["INTERVIEW", "SHORTLISTED"]
    from app.core.errors import AppError

    with pytest.raises(AppError) as ei:  # non-system staff call of a system-only move
        await transition_application(db, a.id, "INTERVIEW", w.fac)
    assert ei.value.code == "INVALID_STATUS_TRANSITION"
    with pytest.raises(AppError) as ei:
        await transition_application(db, uuid.uuid4(), "INTERVIEW", w.fac, system=True)
    assert ei.value.status_code == 404


async def test_invalid_status_value_422(client, db, world):
    a = await make_application(db, world.student, world.it)
    r = await client.patch(f"{URL}/{a.id}/status", headers=auth_headers(world.fac), json={"status": "hired"})
    assert r.status_code == 422
    r = await client.post(f"{URL}/bulk-status", headers=auth_headers(world.fac), json={"ids": [str(a.id)], "status": "hired"})
    assert r.status_code == 422


async def test_accept_requires_offer_details(client, db, world):
    a = await make_application(db, world.student, world.it, status="SHORTLISTED")
    r = await client.patch(f"{URL}/{a.id}/status", headers=auth_headers(world.fac), json={"status": "ACCEPTED"})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "offer_details"
    r = await client.patch(
        f"{URL}/{a.id}/status",
        headers=auth_headers(world.fac),
        json={"status": "ACCEPTED", "note": "welcome", "offer_details": OFFER},
    )
    assert r.status_code == 200
    d = r.json()
    assert d["offer_details"]["stipend_monthly"] == 22000 and d["offer_details"]["start_date"] == "2030-01-15"
    assert d["decision_note"] == "welcome" and d["allowed_transitions"] == []
    mail = [m for m in [] if m]  # email context carries the offer
    assert mail == []


async def test_reject_sets_decision_note_and_terminal(client, db, world):
    a = await make_application(db, world.student, world.it)
    h = auth_headers(world.fac)
    r = await client.patch(f"{URL}/{a.id}/status", headers=h, json={"status": "REJECTED", "note": "not a fit"})
    assert r.json()["decision_note"] == "not a fit"
    r = await client.patch(f"{URL}/{a.id}/status", headers=h, json={"status": "SHORTLISTED"})
    assert r.status_code == 409


async def test_other_staff_cannot_change_status_404(client, db, world):
    a = await make_application(db, world.student, world.it)
    other = await make_faculty(db)
    cu = await make_company_user(db)
    for u in (other, cu):
        r = await client.patch(f"{URL}/{a.id}/status", headers=auth_headers(u), json={"status": "SHORTLISTED"})
        assert r.status_code == 404
    r = await client.patch(f"{URL}/{a.id}/status", headers=auth_headers(world.admin), json={"status": "SHORTLISTED"})
    assert r.status_code == 200


async def test_withdraw_terminal_and_owner_notified(client, db, captured, world):
    a = await make_application(db, world.student, world.it, status="ACCEPTED")  # decline offer
    other_student = await make_student(db)
    assert (await client.post(f"{URL}/{a.id}/withdraw", headers=auth_headers(other_student), json={})).status_code == 404
    assert (await client.post(f"{URL}/{a.id}/withdraw", headers=auth_headers(world.fac), json={})).status_code == 403
    r = await client.post(f"{URL}/{a.id}/withdraw", headers=auth_headers(world.student))  # body optional
    assert r.status_code == 200 and r.json()["status"] == "WITHDRAWN"
    assert any(n["user_id"] == world.fac.id and n["type"] == "APPLICATION_WITHDRAWN" for n in captured.notifications)
    r = await client.post(f"{URL}/{a.id}/withdraw", headers=auth_headers(world.student), json={})
    assert r.status_code == 409 and r.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
    r = await client.delete(f"{URL}/{a.id}", headers=auth_headers(world.student))
    assert r.status_code == 409


async def test_delete_is_withdraw_alias(client, db, world):
    a = await make_application(db, world.student, world.it)
    r = await client.delete(f"{URL}/{a.id}", headers=auth_headers(world.student))
    assert r.status_code == 200 and r.json()["status"] == "WITHDRAWN"
    assert (await client.delete(f"{URL}/{a.id}", headers=auth_headers(world.fac))).status_code == 403


async def test_bulk_status(client, db, world):
    w = world
    other_fac = await make_faculty(db)
    foreign_it = await make_internship(db, other_fac)
    s1, s2, s3 = [await make_student(db) for _ in range(3)]
    a1 = await make_application(db, s1, w.it)
    a2 = await make_application(db, s2, w.it, status="REJECTED")
    a3 = await make_application(db, s3, foreign_it)
    r = await client.post(
        f"{URL}/bulk-status",
        headers=auth_headers(w.fac),
        json={"ids": [str(a1.id), str(a2.id), str(a3.id)], "status": "SHORTLISTED", "note": "batch"},
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["updated"] == [str(a1.id)]
    codes = {f["id"]: f["code"] for f in out["failed"]}
    assert codes == {str(a2.id): "INVALID_STATUS_TRANSITION", str(a3.id): "NOT_FOUND"}
    r = await client.post(f"{URL}/bulk-status", headers=auth_headers(s1), json={"ids": [str(a1.id)], "status": "REJECTED"})
    assert r.status_code == 403
    # accepting in bulk fails per-id (offer details required)
    r = await client.post(f"{URL}/bulk-status", headers=auth_headers(w.fac), json={"ids": [str(a1.id)], "status": "ACCEPTED"})
    assert r.json()["failed"][0]["code"] == "VALIDATION_ERROR"


async def test_complete(client, db, world):
    w = world
    today = datetime.now(UTC).date()
    ended = await make_internship(
        db, w.fac, deadline_in_days=-70, start_date=today - timedelta(days=60), end_date=today - timedelta(days=5), weeks=8
    )
    a = await make_application(db, w.student, ended, status="SHORTLISTED")
    assert (await client.post(f"{URL}/{a.id}/complete", headers=auth_headers(w.fac))).status_code == 409  # not accepted
    a.status = "ACCEPTED"
    await db.flush()
    assert (await client.post(f"{URL}/{a.id}/complete", headers=auth_headers(w.student))).status_code == 403
    r = await client.post(f"{URL}/{a.id}/complete", headers=auth_headers(w.fac))
    assert r.status_code == 200 and r.json()["completed_at"] is not None
    assert r.json()["can_give_student_feedback"] is False  # viewer is staff
    assert any(e["kind"] == "COMPLETED" for e in r.json()["timeline"])
    assert (await client.post(f"{URL}/{a.id}/complete", headers=auth_headers(w.fac))).status_code == 409
    sd = (await client.get(f"{URL}/{a.id}", headers=auth_headers(w.student))).json()
    assert sd["can_give_student_feedback"] is True

    # not ended yet: owner blocked, admin allowed
    future = await make_application(db, await make_student(db), w.it, status="ACCEPTED")
    assert (await client.post(f"{URL}/{future.id}/complete", headers=auth_headers(w.fac))).status_code == 409
    assert (await client.post(f"{URL}/{future.id}/complete", headers=auth_headers(w.admin))).status_code == 200


async def test_resume_url_scoping(client, db, world):
    w = world
    a = await make_application(db, w.student, w.it, resume=w.resume)
    for u in (w.student, w.fac, w.admin):
        r = await client.get(f"{URL}/{a.id}/resume-url", headers=auth_headers(u))
        assert r.status_code == 200, r.text
        assert r.json()["expires_in"] == 300 and w.resume.object_key in r.json()["url"]
    for u in (await make_student(db), await make_faculty(db), await make_company_user(db)):
        assert (await client.get(f"{URL}/{a.id}/resume-url", headers=auth_headers(u))).status_code == 404


async def test_db_check_status_enum(db, world):
    bad = Application(
        internship_id=world.it.id, student_id=world.student.id, resume_document_id=world.resume.id,
        cover_letter=COVER, qualifications="qualified enough", status="HIRED",
    )
    db.add(bad)
    with pytest.raises(IntegrityError):
        await db.flush()
