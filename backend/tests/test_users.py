import uuid

import pytest
from sqlalchemy import func, select

from app.modules.admin.models import AuditLog
from app.modules.auth.models import RefreshToken
from tests.factories import (
    DEFAULT_PASSWORD,
    auth_headers,
    make_admin,
    make_company,
    make_faculty,
    make_student,
    make_user,
)

URL = "/api/v1/users"


def new_user_body(**over):
    body = {"email": "created.by.admin@campushire.dev", "password": "Str0ng!Pass", "full_name": "Created User", "role": "ADMIN", "mark_verified": True}
    body.update(over)
    return body


# ---- authorisation ----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["STUDENT", "FACULTY", "COMPANY"])
async def test_admin_endpoints_forbidden_for_other_roles(client, db, role):
    user = await make_user(db, role)
    target = await make_student(db)
    h = auth_headers(user)
    assert (await client.get(URL, headers=h)).status_code == 403
    assert (await client.post(URL, headers=h, json=new_user_body())).status_code == 403
    assert (await client.get(f"{URL}/{target.id}", headers=h)).status_code == 403
    assert (await client.patch(f"{URL}/{target.id}", headers=h, json={"full_name": "Hacker"})).status_code == 403
    assert (await client.post(f"{URL}/{target.id}/deactivate", headers=h, json={"reason": "x"})).status_code == 403
    assert (await client.post(f"{URL}/{target.id}/activate", headers=h)).status_code == 403
    assert (await client.post(f"{URL}/bulk", headers=h, json={"ids": [str(target.id)], "action": "deactivate"})).status_code == 403


async def test_admin_endpoints_require_auth(client):
    assert (await client.get(URL)).status_code == 401
    assert (await client.patch(f"{URL}/me", json={"full_name": "x y"})).status_code == 401


# ---- list / get -------------------------------------------------------------------------------------------------


async def test_list_users_filters_and_pagination(client, db):
    admin = await make_admin(db)
    for i in range(3):
        await make_student(db, full_name=f"Zed Student {i}")
    await make_faculty(db, full_name="Prof Quokka")
    await make_student(db, is_active=False, full_name="Zed Gone")

    r = await client.get(URL, headers=auth_headers(admin), params={"page_size": 2})
    body = r.json()
    assert r.status_code == 200
    assert set(body) == {"items", "total", "page", "page_size", "pages"}
    assert len(body["items"]) == 2 and body["page_size"] == 2 and body["pages"] == (body["total"] + 1) // 2
    assert set(body["items"][0]) == {"id", "email", "role", "phone", "full_name", "is_active", "email_verified", "last_login_at", "created_at"}
    assert "password_hash" not in r.text

    r = await client.get(URL, headers=auth_headers(admin), params={"role": "FACULTY"})
    assert [u["full_name"] for u in r.json()["items"]] == ["Prof Quokka"]
    r = await client.get(URL, headers=auth_headers(admin), params={"q": "zed", "is_active": "true"})
    assert r.json()["total"] == 3
    r = await client.get(URL, headers=auth_headers(admin), params={"q": "zed", "is_active": "false"})
    assert r.json()["total"] == 1
    r = await client.get(URL, headers=auth_headers(admin), params={"page": 0})
    assert r.status_code == 422
    r = await client.get(URL, headers=auth_headers(admin), params={"page_size": 101})
    assert r.status_code == 422


async def test_get_user_detail_includes_profile(client, db):
    admin = await make_admin(db)
    student = await make_student(db, department="ECE", gpa="3.25")
    r = await client.get(f"{URL}/{student.id}", headers=auth_headers(admin))
    assert r.status_code == 200
    body = r.json()
    assert body["student"]["department"] == "ECE" and body["student"]["gpa"] == 3.25
    assert (await client.get(f"{URL}/{uuid.uuid4()}", headers=auth_headers(admin))).status_code == 404


# ---- create -----------------------------------------------------------------------------------------------------


async def test_admin_creates_faculty_verified_and_they_can_login(client, db):
    admin = await make_admin(db)
    body = new_user_body(email="dr.rao@campushire.dev", full_name="Dr Rao", role="FACULTY", faculty={"department": "CSE", "designation": "Professor"}, phone="+91 98765 43210")
    r = await client.post(URL, headers=auth_headers(admin), json=body)
    assert r.status_code == 201, r.text
    assert r.json()["faculty"]["department"] == "CSE" and r.json()["email_verified"] is True
    assert r.json()["phone"] == "+919876543210"
    login = await client.post("/api/v1/auth/login", json={"email": "dr.rao@campushire.dev", "password": "Str0ng!Pass"})
    assert login.status_code == 200 and login.json()["user"]["role"] == "FACULTY"
    audit = (await db.execute(select(func.count()).select_from(AuditLog).where(AuditLog.action == "user.create", AuditLog.actor_id == admin.id))).scalar_one()
    assert audit == 1


async def test_admin_creates_unverified_student_sends_verification_email(client, db, captured):
    admin = await make_admin(db)
    body = new_user_body(email="stu@campushire.dev", role="STUDENT", mark_verified=False, student={"department": "IT", "gpa": 3.1})
    r = await client.post(URL, headers=auth_headers(admin), json=body)
    assert r.status_code == 201
    assert r.json()["email_verified"] is False and r.json()["student"]["gpa"] == 3.1
    assert len(captured.emails_to("stu@campushire.dev", "verify_email")) == 1
    login = await client.post("/api/v1/auth/login", json={"email": "stu@campushire.dev", "password": "Str0ng!Pass"})
    assert login.status_code == 403 and login.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"


async def test_admin_creates_company_member(client, db):
    admin = await make_admin(db)
    company = await make_company(db)
    body = new_user_body(email="recruiter@campushire.dev", role="COMPANY", company={"company_id": str(company.id), "job_title": "Recruiter"})
    r = await client.post(URL, headers=auth_headers(admin), json=body)
    assert r.status_code == 201, r.text
    assert r.json()["company"]["company_id"] == str(company.id)
    assert r.json()["company"]["company_name"] == company.name


async def test_create_requires_role_specific_block(client, db):
    admin = await make_admin(db)
    for role in ("STUDENT", "FACULTY", "COMPANY"):
        r = await client.post(URL, headers=auth_headers(admin), json=new_user_body(email=f"{role.lower()}@campushire.dev", role=role))
        assert r.status_code == 422, role
        assert r.json()["error"]["details"][0]["field"] == role.lower()
    r = await client.post(URL, headers=auth_headers(admin), json=new_user_body(role="COMPANY", company={"company_id": str(uuid.uuid4())}))
    assert r.status_code == 422


async def test_create_duplicate_email_and_weak_password(client, db):
    admin = await make_admin(db)
    existing = await make_student(db)
    r = await client.post(URL, headers=auth_headers(admin), json=new_user_body(email=existing.email.upper()))
    assert r.status_code == 409 and r.json()["error"]["code"] == "DUPLICATE_EMAIL"
    r = await client.post(URL, headers=auth_headers(admin), json=new_user_body(password="weak"))
    assert r.status_code == 422


# ---- update -----------------------------------------------------------------------------------------------------


async def test_admin_patch_user_and_profile(client, db):
    admin = await make_admin(db)
    student = await make_student(db, department="CSE", gpa="3.00", phone="+919876543210")
    r = await client.patch(
        f"{URL}/{student.id}",
        headers=auth_headers(admin),
        json={"full_name": "Renamed Student", "phone": None, "student": {"gpa": 3.9, "skills": ["Python", "SQL"], "department": "IT"}},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["full_name"] == "Renamed Student" and body["phone"] is None
    assert body["student"]["gpa"] == 3.9 and body["student"]["skills"] == ["Python", "SQL"] and body["student"]["department"] == "IT"


async def test_admin_patch_validation_and_role_mismatch(client, db):
    admin = await make_admin(db)
    student = await make_student(db)
    faculty = await make_faculty(db)
    h = auth_headers(admin)
    assert (await client.patch(f"{URL}/{student.id}", headers=h, json={"student": {"gpa": 4.5}})).status_code == 422
    assert (await client.patch(f"{URL}/{student.id}", headers=h, json={"phone": "123"})).status_code == 422
    assert (await client.patch(f"{URL}/{faculty.id}", headers=h, json={"student": {"gpa": 3.0}})).status_code == 400
    assert (await client.patch(f"{URL}/{uuid.uuid4()}", headers=h, json={"full_name": "Ghost User"})).status_code == 404


async def test_patch_me(client, db):
    student = await make_student(db)
    r = await client.patch(f"{URL}/me", headers=auth_headers(student), json={"full_name": "My New Name", "phone": "9876543210", "avatar_url": "https://img.campushire.dev/a.png"})
    assert r.status_code == 200, r.text
    assert r.json()["full_name"] == "My New Name" and r.json()["phone"] == "9876543210"
    assert r.json()["avatar_url"] == "https://img.campushire.dev/a.png"
    bad = await client.patch(f"{URL}/me", headers=auth_headers(student), json={"phone": "abc"})
    assert bad.status_code == 422
    # role / email / is_active are not editable through this endpoint (extra fields ignored)
    r = await client.patch(f"{URL}/me", headers=auth_headers(student), json={"role": "ADMIN", "email": "x@y.zz"})
    assert r.status_code == 200 and r.json()["role"] == "STUDENT"


# ---- deactivate / activate / bulk -----------------------------------------------------------------------------------


async def test_deactivate_blocks_login_and_revokes_tokens_then_activate(client, db):
    admin = await make_admin(db)
    student = await make_student(db)
    login = await client.post("/api/v1/auth/login", json={"email": student.email, "password": DEFAULT_PASSWORD})
    assert login.status_code == 200

    r = await client.post(f"{URL}/{student.id}/deactivate", headers=auth_headers(admin), json={"reason": "Left the college"})
    assert r.status_code == 200 and r.json()["is_active"] is False
    detail = (await client.get(f"{URL}/{student.id}", headers=auth_headers(admin))).json()
    assert detail["deactivated_reason"] == "Left the college" and detail["deactivated_at"]

    again = await client.post("/api/v1/auth/login", json={"email": student.email, "password": DEFAULT_PASSWORD})
    assert again.status_code == 403 and again.json()["error"]["code"] == "ACCOUNT_DEACTIVATED"
    assert (await client.get("/api/v1/auth/me", headers=auth_headers(student))).status_code == 403
    live = (await db.execute(select(func.count()).select_from(RefreshToken).where(RefreshToken.user_id == student.id, RefreshToken.revoked_at.is_(None)))).scalar_one()
    assert live == 0

    r = await client.post(f"{URL}/{student.id}/activate", headers=auth_headers(admin))
    assert r.status_code == 200 and r.json()["is_active"] is True
    assert (await client.post("/api/v1/auth/login", json={"email": student.email, "password": DEFAULT_PASSWORD})).status_code == 200
    actions = {a for (a,) in (await db.execute(select(AuditLog.action).where(AuditLog.entity_id == student.id))).all()}
    assert {"user.deactivate", "user.activate"} <= actions


async def test_cannot_deactivate_self(client, db):
    admin = await make_admin(db)
    r = await client.post(f"{URL}/{admin.id}/deactivate", headers=auth_headers(admin), json={"reason": "oops"})
    assert r.status_code == 400
    assert (await client.get("/api/v1/auth/me", headers=auth_headers(admin))).status_code == 200


async def test_deactivate_requires_reason_and_existing_user(client, db):
    admin = await make_admin(db)
    student = await make_student(db)
    assert (await client.post(f"{URL}/{student.id}/deactivate", headers=auth_headers(admin), json={})).status_code == 422
    assert (await client.post(f"{URL}/{uuid.uuid4()}/deactivate", headers=auth_headers(admin), json={"reason": "x"})).status_code == 404


async def test_bulk_deactivate_and_activate(client, db):
    admin = await make_admin(db)
    s1, s2 = await make_student(db), await make_student(db)
    ghost = uuid.uuid4()
    h = auth_headers(admin)
    r = await client.post(f"{URL}/bulk", headers=h, json={"ids": [str(s1.id), str(s2.id), str(ghost), str(admin.id)], "action": "deactivate"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body["updated"]) == {str(s1.id), str(s2.id)}
    assert {f["id"]: f["code"] for f in body["failed"]} == {str(ghost): "NOT_FOUND", str(admin.id): "BAD_REQUEST"}
    assert (await client.get(f"{URL}/{s1.id}", headers=h)).json()["is_active"] is False

    r = await client.post(f"{URL}/bulk", headers=h, json={"ids": [str(s1.id), str(s2.id)], "action": "activate"})
    assert set(r.json()["updated"]) == {str(s1.id), str(s2.id)} and r.json()["failed"] == []
    assert (await client.post(f"{URL}/bulk", headers=h, json={"ids": [], "action": "activate"})).status_code == 422
    assert (await client.post(f"{URL}/bulk", headers=h, json={"ids": [str(s1.id)], "action": "delete"})).status_code == 422
