"""Students (profile CRUD, scoping, deactivate, history) and faculty profile endpoints (plan 4.4, V6)."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.admin.models import AuditLog
from app.modules.students.models import Student
from sqlalchemy import select
from tests.factories import (
    DEFAULT_PASSWORD,
    auth_headers,
    make_admin,
    make_application,
    make_company_user,
    make_faculty,
    make_internship,
    make_resume,
    make_student,
)

URL = "/api/v1/students"


# ---- /me --------------------------------------------------------------------------------------------------------------
async def test_me_returns_profile_stats_and_default_resume(client, db):
    student = await make_student(db, department="ECE", gpa="3.25", full_name="Mia Me", phone="+919876543210")
    resume = await make_resume(db, student)
    student.profile.default_resume_id = resume.id
    fac = await make_faculty(db)
    await make_application(db, student, await make_internship(db, fac), status="SHORTLISTED")
    r = await client.get(f"{URL}/me", headers=auth_headers(student))
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["user_id"] == str(student.id) and me["department"] == "ECE"
    assert me["gpa"] == 3.25 and isinstance(me["gpa"], float)  # number, not string
    assert me["default_resume"]["id"] == str(resume.id) and me["default_resume"]["kind"] == "RESUME"
    assert me["full_name"] == "Mia Me" and me["email"] == student.email and me["phone"] == "+919876543210"
    assert me["stats"]["total_applications"] == 1
    assert me["stats"]["by_status"]["SHORTLISTED"] == 1 and me["stats"]["by_status"]["PENDING"] == 0
    assert set(me["stats"]["by_status"]) == {"PENDING", "UNDER_REVIEW", "SHORTLISTED", "INTERVIEW", "ACCEPTED", "REJECTED", "WITHDRAWN"}


@pytest.mark.parametrize("role", ["ADMIN", "FACULTY", "COMPANY"])
async def test_me_student_only(client, db, role):
    user = await (make_admin(db) if role == "ADMIN" else make_faculty(db) if role == "FACULTY" else make_company_user(db))
    assert (await client.get(f"{URL}/me", headers=auth_headers(user))).status_code == 403
    assert (await client.patch(f"{URL}/me", headers=auth_headers(user), json={"bio": "x"})).status_code == 403


async def test_me_requires_auth(client):
    assert (await client.get(f"{URL}/me")).status_code == 401


async def test_update_me(client, db):
    student = await make_student(db)
    payload = {
        "phone": "+1 (415) 555-2671",
        "department": "Mechanical",
        "gpa": 3.9,
        "graduation_year": 2027,
        "skills": ["Python", "python", "SQL", " Go "],
        "bio": "Curious engineer",
        "linkedin_url": "https://linkedin.com/in/me",
        "github_url": "https://github.com/me",
        "portfolio_url": "",
    }
    r = await client.patch(f"{URL}/me", headers=auth_headers(student), json=payload)
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["phone"] == "+14155552671"  # normalised to E.164
    assert me["department"] == "Mechanical" and me["gpa"] == 3.9 and me["graduation_year"] == 2027
    assert me["skills"] == ["Python", "SQL", "Go"]  # trimmed and de-duplicated case-insensitively
    assert me["portfolio_url"] is None and me["linkedin_url"] == "https://linkedin.com/in/me"
    # partial update leaves the rest untouched; null clears nullable fields
    r = await client.patch(f"{URL}/me", headers=auth_headers(student), json={"bio": None, "skills": []})
    assert r.json()["bio"] is None and r.json()["skills"] == [] and r.json()["gpa"] == 3.9
    audits = (await db.execute(select(AuditLog).where(AuditLog.action == "student.update_profile"))).scalars().all()
    assert len(audits) == 2 and audits[0].entity_id == student.id


@pytest.mark.parametrize("gpa", [-0.1, 4.01, 5, "abc"])
async def test_gpa_bounds_rejected(client, db, gpa):
    student = await make_student(db)
    r = await client.patch(f"{URL}/me", headers=auth_headers(student), json={"gpa": gpa})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("gpa", [0, 0.0, 4, 4.0, 3.99])
async def test_gpa_bounds_accepted(client, db, gpa):
    student = await make_student(db)
    r = await client.patch(f"{URL}/me", headers=auth_headers(student), json={"gpa": gpa})
    assert r.status_code == 200, r.text
    assert r.json()["gpa"] == float(gpa)


async def test_gpa_db_check_constraint(db):
    user = await make_student(db)
    user.profile.gpa = Decimal("4.50")
    with pytest.raises(IntegrityError) as exc:
        await db.flush()
    assert "ck_students_gpa" in str(exc.value)
    await db.rollback()


@pytest.mark.parametrize(
    "payload",
    [
        {"phone": "12345"},
        {"phone": "abcdefghijk"},
        {"phone": "+1234567890123456"},
        {"graduation_year": 1999},
        {"graduation_year": 2101},
        {"bio": "x" * 2001},
        {"linkedin_url": "not-a-url"},
        {"github_url": "ftp://x.y"},
        {"skills": ["ok", ""]},
    ],
)
async def test_update_me_validation_422(client, db, payload):
    student = await make_student(db)
    r = await client.patch(f"{URL}/me", headers=auth_headers(student), json=payload)
    assert r.status_code == 422, payload


async def test_set_default_resume(client, db):
    student, other = await make_student(db), await make_student(db)
    mine = await make_resume(db, student)
    theirs = await make_resume(db, other)
    pending = await make_resume(db, student, status="PENDING_UPLOAD")
    h = auth_headers(student)
    r = await client.put(f"{URL}/me/resume", headers=h, json={"document_id": str(mine.id)})
    assert r.status_code == 200 and r.json()["default_resume"]["id"] == str(mine.id)
    for bad in (theirs.id, pending.id, uuid.uuid4()):
        r = await client.put(f"{URL}/me/resume", headers=h, json={"document_id": str(bad)})
        assert r.status_code == 422 and r.json()["error"]["code"] == "RESUME_INVALID"
    assert (await client.put(f"{URL}/me/resume", headers=h, json={})).status_code == 422
    assert (await client.get(f"{URL}/me", headers=h)).json()["default_resume"]["id"] == str(mine.id)


# ---- list ------------------------------------------------------------------------------------------------------------------
async def test_list_admin_sees_all_with_filters(client, db):
    admin = await make_admin(db)
    a = await make_student(db, full_name="Alice Zephyr", department="CSE", gpa="3.9", enrollment_no="EN-A-1")
    b = await make_student(db, full_name="Bob Zephyr", department="ECE", gpa="2.5", is_active=False)
    fac = await make_faculty(db)
    await make_application(db, a, await make_internship(db, fac), status="ACCEPTED")
    h = auth_headers(admin)

    r = await client.get(URL, headers=h, params={"q": "zephyr"})
    body = r.json()
    assert body["total"] == 2 and [i["full_name"] for i in body["items"]] == ["Alice Zephyr", "Bob Zephyr"]
    alice = body["items"][0]
    assert alice["application_count"] == 1 and alice["placed"] is True and alice["gpa"] == 3.9
    assert body["items"][1]["is_active"] is False and body["items"][1]["placed"] is False
    assert (await client.get(URL, headers=h, params={"q": "zephyr", "department": "ECE"})).json()["total"] == 1
    assert (await client.get(URL, headers=h, params={"q": "zephyr", "gpa_min": 3})).json()["total"] == 1
    assert (await client.get(URL, headers=h, params={"q": "zephyr", "gpa_max": 3})).json()["items"][0]["user_id"] == str(b.id)
    assert (await client.get(URL, headers=h, params={"q": "EN-A"})).json()["total"] == 1
    assert (await client.get(URL, headers=h, params={"q": "100%"})).json()["total"] == 0  # LIKE wildcards are escaped
    assert (await client.get(URL, headers=h, params={"gpa_min": 5})).status_code == 422
    assert (await client.get(URL, headers=h, params={"page_size": 1})).json()["pages"] >= 2


async def test_list_faculty_only_sees_own_applicants(client, db):
    fac_a, fac_b = await make_faculty(db), await make_faculty(db)
    s1, s2, s3 = await make_student(db), await make_student(db), await make_student(db)
    ia, ib = await make_internship(db, fac_a), await make_internship(db, fac_b)
    await make_application(db, s1, ia)
    await make_application(db, s1, ib)
    await make_application(db, s2, ib)
    r = await client.get(URL, headers=auth_headers(fac_a))
    body = r.json()
    assert [i["user_id"] for i in body["items"]] == [str(s1.id)]
    assert body["items"][0]["application_count"] == 1  # only applications to fac_a's internships
    assert {i["user_id"] for i in (await client.get(URL, headers=auth_headers(fac_b))).json()["items"]} == {str(s1.id), str(s2.id)}
    assert str(s3.id) not in str(r.json())


@pytest.mark.parametrize("role", ["STUDENT", "COMPANY"])
async def test_list_forbidden_for_student_and_company(client, db, role):
    user = await (make_student(db) if role == "STUDENT" else make_company_user(db))
    assert (await client.get(URL, headers=auth_headers(user))).status_code == 403
    assert (await client.get(URL)).status_code == 401


# ---- detail ------------------------------------------------------------------------------------------------------------------
async def test_get_student_scoping(client, db):
    admin = await make_admin(db)
    fac_a, fac_b = await make_faculty(db), await make_faculty(db)
    comp, other_comp = await make_company_user(db), await make_company_user(db)
    student, nosy = await make_student(db), await make_student(db)
    ia = await make_internship(db, fac_a)
    ic = await make_internship(db, comp, company=comp.company)
    await make_application(db, student, ia, status="SHORTLISTED")
    await make_application(db, student, ic)
    url = f"{URL}/{student.id}"

    r = await client.get(url, headers=auth_headers(admin))
    assert r.status_code == 200
    d = r.json()
    assert d["profile"]["user_id"] == str(student.id) and d["stats"]["total_applications"] == 2
    assert d["application_count"] == 2 and d["gpa"] == 3.5

    # staff see the profile, but only the stats of applications to their own internships
    r = await client.get(url, headers=auth_headers(fac_a))
    assert r.status_code == 200
    assert r.json()["stats"]["total_applications"] == 1 and r.json()["stats"]["by_status"]["SHORTLISTED"] == 1
    assert (await client.get(url, headers=auth_headers(comp))).status_code == 200
    # outside scope -> 404 (not 403)
    assert (await client.get(url, headers=auth_headers(fac_b))).status_code == 404
    assert (await client.get(url, headers=auth_headers(other_comp))).status_code == 404
    # students may not use this endpoint at all
    assert (await client.get(url, headers=auth_headers(nosy))).status_code == 403
    assert (await client.get(f"{URL}/{uuid.uuid4()}", headers=auth_headers(admin))).status_code == 404
    assert (await client.get(f"{URL}/not-a-uuid", headers=auth_headers(admin))).status_code == 422


async def test_admin_update_student(client, db):
    admin, fac = await make_admin(db), await make_faculty(db)
    student = await make_student(db, enrollment_no="EN-1")
    other = await make_student(db, enrollment_no="EN-2")
    url = f"{URL}/{student.id}"
    r = await client.patch(
        url, headers=auth_headers(admin), json={"full_name": "Renamed Student", "gpa": 3.1, "enrollment_no": "EN-9"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["full_name"] == "Renamed Student" and r.json()["gpa"] == 3.1
    assert r.json()["profile"]["enrollment_no"] == "EN-9"
    dup = await client.patch(url, headers=auth_headers(admin), json={"enrollment_no": "EN-2"})
    assert dup.status_code == 409
    assert (await client.patch(url, headers=auth_headers(admin), json={"gpa": 4.5})).status_code == 422
    assert (await client.patch(url, headers=auth_headers(fac), json={"gpa": 3.0})).status_code == 403
    assert (await client.patch(url, headers=auth_headers(other), json={"gpa": 3.0})).status_code == 403
    assert (await client.patch(f"{URL}/{uuid.uuid4()}", headers=auth_headers(admin), json={"gpa": 3})).status_code == 404


# ---- deactivate ---------------------------------------------------------------------------------------------------------------
async def test_deactivate_student_blocks_login_and_api(client, db):
    admin, fac = await make_admin(db), await make_faculty(db)
    student = await make_student(db)
    url = f"{URL}/{student.id}/deactivate"
    assert (await client.post(url, headers=auth_headers(fac), json={"reason": "x"})).status_code == 403
    assert (await client.post(url, headers=auth_headers(student), json={"reason": "x"})).status_code == 403
    assert (await client.post(url, headers=auth_headers(admin), json={})).status_code == 422
    assert (await client.post(f"{URL}/{fac.id}/deactivate", headers=auth_headers(admin), json={"reason": "x"})).status_code == 404

    token_headers = auth_headers(student)
    r = await client.post(url, headers=auth_headers(admin), json={"reason": "Left the college"})
    assert r.status_code == 200, r.text
    await db.refresh(student)
    assert student.is_active is False and student.deactivated_reason == "Left the college"
    login = await client.post("/api/v1/auth/login", json={"email": student.email, "password": DEFAULT_PASSWORD})
    assert login.status_code == 403 and login.json()["error"]["code"] == "ACCOUNT_DEACTIVATED"
    assert (await client.get(f"{URL}/me", headers=token_headers)).status_code == 403
    actions = {a.action for a in (await db.execute(select(AuditLog).where(AuditLog.entity_id == student.id))).scalars()}
    assert {"student.deactivate", "user.deactivate"} <= actions


# ---- application history ------------------------------------------------------------------------------------------------------------
async def test_application_history_scoping_and_shape(client, db):
    admin, fac = await make_admin(db), await make_faculty(db)
    student, other = await make_student(db, full_name="Hist Student"), await make_student(db)
    i1, i2 = await make_internship(db, fac), await make_internship(db, fac)
    await make_application(db, student, i1)
    await make_application(db, student, i2, status="REJECTED")
    url = f"{URL}/{student.id}/applications"

    for who in (student, admin):
        r = await client.get(url, headers=auth_headers(who))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 2 and len(body["items"]) == 2
        item = body["items"][0]
        assert set(item) >= {"id", "status", "status_changed_at", "created_at", "internship", "student", "next_interview_at", "evaluation_avg"}
        assert item["student"]["full_name"] == "Hist Student" and item["student"]["gpa"] == 3.5
        assert item["internship"]["company_logo_url"] is None and item["internship"]["title"].startswith("Software")
    assert {i["status"] for i in (await client.get(url, headers=auth_headers(student))).json()["items"]} == {"PENDING", "REJECTED"}
    assert (await client.get(url, headers=auth_headers(other))).status_code == 404  # another student
    assert (await client.get(url, headers=auth_headers(fac))).status_code == 403
    assert (await client.get(f"{URL}/{uuid.uuid4()}/applications", headers=auth_headers(admin))).status_code == 404


# ---- faculty ------------------------------------------------------------------------------------------------------------------------
async def test_faculty_endpoints(client, db):
    admin, student = await make_admin(db), await make_student(db)
    fac = await make_faculty(db, full_name="Prof Quasar", department="Physics")
    other = await make_faculty(db, full_name="Prof Other")
    other.profile.employee_id = "EMP-77"
    await db.flush()
    base = "/api/v1/faculty"

    r = await client.get(f"{base}/me", headers=auth_headers(fac))
    assert r.status_code == 200 and r.json()["department"] == "Physics" and r.json()["user_id"] == str(fac.id)
    r = await client.patch(
        f"{base}/me", headers=auth_headers(fac), json={"designation": "Dean", "employee_id": "EMP-1", "department": "Math"}
    )
    assert r.status_code == 200 and r.json() == {"user_id": str(fac.id), "department": "Math", "designation": "Dean", "employee_id": "EMP-1"}
    assert (await client.patch(f"{base}/me", headers=auth_headers(fac), json={"employee_id": "EMP-77"})).status_code == 409
    assert (await client.patch(f"{base}/me", headers=auth_headers(fac), json={"department": ""})).status_code == 422
    r = await client.patch(f"{base}/me", headers=auth_headers(fac), json={"designation": None})
    assert r.json()["designation"] is None

    r = await client.get(base, headers=auth_headers(admin), params={"q": "quasar"})
    assert r.status_code == 200 and r.json()["total"] == 1
    item = r.json()["items"][0]
    assert item["full_name"] == "Prof Quasar" and item["email"] == fac.email and item["user_id"] == str(fac.id)
    assert (await client.get(base, headers=auth_headers(admin))).json()["total"] >= 2

    for who in (student, fac):
        assert (await client.get(base, headers=auth_headers(who))).status_code == 403
    for who in (student, admin):
        assert (await client.get(f"{base}/me", headers=auth_headers(who))).status_code == 403
        assert (await client.patch(f"{base}/me", headers=auth_headers(who), json={"designation": "x"})).status_code == 403
    assert (await client.get(f"{base}/me")).status_code == 401
