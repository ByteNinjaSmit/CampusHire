import re
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.modules.admin.models import AuditLog, LoginEvent
from app.modules.auth.models import RefreshToken
from app.modules.companies.models import Company, CompanyMember
from app.modules.notifications.models import Notification
from app.modules.students.models import Student
from app.modules.users.models import User
from tests.factories import DEFAULT_PASSWORD, auth_headers, make_admin, make_student, make_user, unique_cin

CSRF = {"X-Requested-With": "campushire"}


def student_payload(**over):
    body = {
        "email": "new.student@campushire.dev",
        "password": "Str0ng!Pass",
        "full_name": "New Student",
        "phone": "+91 98765 43210",
        "department": "CSE",
        "gpa": 3.6,
    }
    body.update(over)
    return body


def company_payload(**over):
    body = {
        "email": "hr@acme-labs.dev",
        "password": "Str0ng!Pass",
        "full_name": "Hiring Manager",
        "phone": "9876543210",
        "job_title": "HR Lead",
        "company": {
            "name": "Acme Labs",
            "registration_number": unique_cin().lower(),
            "location": "Pune, India",
            "industry": "Software",
            "website": "https://acme-labs.dev",
            "contact_person_name": "Hiring Manager",
            "contact_email": "contact@acme-labs.dev",
            "contact_phone": "+91 98765 43210",
        },
    }
    body.update(over)
    return body


def refresh_cookie(resp) -> str:
    for h in resp.headers.get_list("set-cookie"):
        m = re.match(r"ch_refresh=([^;]*)", h)
        if m and m.group(1) and "Max-Age=0" not in h:
            return m.group(1)
    raise AssertionError("no ch_refresh cookie set")


def cookie_header(raw: str) -> dict[str, str]:
    return {"Cookie": f"ch_refresh={raw}", **CSRF}


async def login(client, email, password=DEFAULT_PASSWORD):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


# ---- registration -----------------------------------------------------------------------------------------


async def test_register_student_creates_user_profile_and_sends_verification(client, db, captured):
    r = await client.post("/api/v1/auth/register/student", json=student_payload())
    assert r.status_code == 201, r.text
    assert "message" in r.json()
    user = (await db.execute(select(User).where(User.email == "new.student@campushire.dev"))).scalar_one()
    assert user.role == "STUDENT" and user.email_verified_at is None
    assert user.phone == "+919876543210"  # normalised to E.164
    st = (await db.execute(select(Student).where(Student.user_id == user.id))).scalar_one()
    assert st.department == "CSE" and float(st.gpa) == 3.6
    mails = captured.emails_to("new.student@campushire.dev", "verify_email")
    assert len(mails) == 1
    assert mails[0]["context"]["verify_url"].startswith(f"{settings.FRONTEND_URL}/verify-email?token=")


@pytest.mark.parametrize("bad", ["plainaddress", "a@b", "a..b@c.com", "a@b..com"])
async def test_register_invalid_email_422(client, bad):
    r = await client.post("/api/v1/auth/register/student", json=student_payload(email=bad))
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert any(d["field"] == "email" for d in err["details"])
    assert err["request_id"]


async def test_register_duplicate_email_409_case_insensitive(client):
    assert (await client.post("/api/v1/auth/register/student", json=student_payload(email="Foo@campushire.dev"))).status_code == 201
    r = await client.post("/api/v1/auth/register/student", json=student_payload(email="foo@campushire.dev"))
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "DUPLICATE_EMAIL"


@pytest.mark.parametrize(
    ("field", "value"),
    [("password", "weakpass"), ("phone", "12345"), ("gpa", 4.5), ("gpa", -0.1), ("full_name", "A"), ("graduation_year", 1999)],
)
async def test_register_student_validation_422(client, field, value):
    r = await client.post("/api/v1/auth/register/student", json=student_payload(**{field: value}))
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_register_student_gpa_bounds_inclusive(client):
    assert (await client.post("/api/v1/auth/register/student", json=student_payload(email="g0@campushire.dev", gpa=0))).status_code == 201
    assert (await client.post("/api/v1/auth/register/student", json=student_payload(email="g4@campushire.dev", gpa=4.0))).status_code == 201


async def test_register_company_creates_pending_company_and_notifies_admin(client, db, captured):
    admin = await make_admin(db)
    r = await client.post("/api/v1/auth/register/company", json=company_payload())
    assert r.status_code == 201, r.text
    user = (await db.execute(select(User).where(User.email == "hr@acme-labs.dev"))).scalar_one()
    assert user.role == "COMPANY"
    member = (await db.execute(select(CompanyMember).where(CompanyMember.user_id == user.id))).scalar_one()
    company = (await db.execute(select(Company).where(Company.id == member.company_id))).scalar_one()
    assert company.status == "PENDING"
    assert company.registration_number == company.registration_number.upper()
    assert company.created_by == user.id
    notes = (await db.execute(select(Notification).where(Notification.user_id == admin.id))).scalars().all()
    assert any(n.type == "COMPANY_REGISTERED" for n in notes)
    assert captured.emails_to("hr@acme-labs.dev", "verify_email")


async def test_register_company_duplicate_registration_number_409(client):
    payload = company_payload()
    assert (await client.post("/api/v1/auth/register/company", json=payload)).status_code == 201
    second = company_payload(email="hr2@acme-labs.dev")
    second["company"]["registration_number"] = payload["company"]["registration_number"].upper()
    r = await client.post("/api/v1/auth/register/company", json=second)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "DUPLICATE_REGISTRATION_NUMBER"


async def test_register_company_invalid_registration_number_422(client):
    payload = company_payload()
    payload["company"]["registration_number"] = "ABC"
    r = await client.post("/api/v1/auth/register/company", json=payload)
    assert r.status_code == 422
    assert any("registration_number" in d["field"] for d in r.json()["error"]["details"])


# ---- email verification -----------------------------------------------------------------------------------


async def test_login_unverified_403(client, db):
    user = await make_user(db, "STUDENT", verified=False)
    r = await login(client, user.email)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"


async def test_verify_email_flow(client, db, captured):
    assert (await client.post("/api/v1/auth/register/student", json=student_payload())).status_code == 201
    token = captured.emails_to("new.student@campushire.dev")[0]["context"]["verify_url"].split("token=")[1]
    assert (await login(client, "new.student@campushire.dev", "Str0ng!Pass")).status_code == 403

    r = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert r.status_code == 200, r.text
    ok = await login(client, "new.student@campushire.dev", "Str0ng!Pass")
    assert ok.status_code == 200
    # token is single use, but re-clicking the link for an already-verified account is harmless
    again = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert again.status_code == 200


async def test_verify_email_bad_token_400(client):
    r = await client.post("/api/v1/auth/verify-email", json={"token": "x" * 40})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "BAD_REQUEST"


async def test_verify_email_expired_token(client, db, captured):
    user = await make_user(db, "STUDENT", verified=False)
    from app.modules.auth.emails import send_verification_email
    from app.modules.auth.models import UserToken

    await send_verification_email(db, user)
    await db.flush()
    tok = (await db.execute(select(UserToken).where(UserToken.user_id == user.id))).scalar_one()
    tok.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await db.flush()
    from app.core import side_effects

    await side_effects.flush(db)
    raw = captured.emails[0]["context"]["verify_url"].split("token=")[1]
    r = await client.post("/api/v1/auth/verify-email", json={"token": raw})
    assert r.status_code == 400


async def test_resend_verification_always_202(client, db, captured):
    user = await make_user(db, "STUDENT", verified=False)
    r1 = await client.post("/api/v1/auth/resend-verification", json={"email": user.email})
    r2 = await client.post("/api/v1/auth/resend-verification", json={"email": "ghost@campushire.dev"})
    assert r1.status_code == r2.status_code == 202
    assert r1.json() == r2.json()
    assert len(captured.emails_to(user.email, "verify_email")) == 1
    assert captured.emails_to("ghost@campushire.dev") == []


# ---- login ----------------------------------------------------------------------------------------------------


async def test_login_success_sets_cookies_and_returns_me(client, db):
    user = await make_student(db)
    r = await login(client, user.email.upper())  # case-insensitive
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == settings.JWT_ACCESS_TTL_SECONDS
    assert body["user"]["email"] == user.email and body["user"]["role"] == "STUDENT"
    assert body["user"]["email_verified"] is True
    assert body["user"]["student"]["department"] == "CSE" and body["user"]["student"]["gpa"] == 3.5
    cookies = r.headers.get_list("set-cookie")
    refresh = next(c for c in cookies if c.startswith("ch_refresh="))
    assert "HttpOnly" in refresh and "Path=/api/v1/auth" in refresh and "SameSite=lax" in refresh
    assert f"Max-Age={settings.REFRESH_TTL_DAYS * 86400}" in refresh
    role = next(c for c in cookies if c.startswith("ch_role="))
    assert "ch_role=STUDENT" in role and "HttpOnly" not in role and "Path=/;" in role + ";"
    ev = (await db.execute(select(LoginEvent).where(LoginEvent.user_id == user.id))).scalars().all()
    assert len(ev) == 1 and ev[0].success is True
    assert (await db.execute(select(User.last_login_at).where(User.id == user.id))).scalar_one() is not None


async def test_login_wrong_password_and_unknown_user_are_indistinguishable(client, db):
    user = await make_student(db)
    bad_pw = await login(client, user.email, "Wrong!Pass1")
    ghost = await login(client, "ghost@campushire.dev", "Wrong!Pass1")
    assert bad_pw.status_code == ghost.status_code == 401
    assert bad_pw.json()["error"]["code"] == ghost.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert bad_pw.json()["error"]["message"] == ghost.json()["error"]["message"]
    failed = (await db.execute(select(func.count()).select_from(LoginEvent).where(LoginEvent.success.is_(False)))).scalar_one()
    assert failed == 2  # failures are persisted even though the response is an error


async def test_login_deactivated_403(client, db):
    user = await make_student(db, is_active=False)
    r = await login(client, user.email)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "ACCOUNT_DEACTIVATED"


async def test_login_creates_audit_row(client, db):
    user = await make_student(db)
    await login(client, user.email)
    rows = (await db.execute(select(AuditLog).where(AuditLog.action == "auth.login", AuditLog.actor_id == user.id))).scalars().all()
    assert len(rows) == 1


async def test_password_hash_is_argon2id(db):
    user = await make_user(db, "STUDENT", password="Another!Pass1")
    assert user.password_hash.startswith("$argon2id$")


async def test_rate_limit_login_429(client, db, enable_rate_limit):
    user = await make_student(db)
    for _ in range(5):
        r = await login(client, user.email, "Wrong!Pass1")
        assert r.status_code == 401
    r = await login(client, user.email, "Wrong!Pass1")
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "RATE_LIMITED"
    assert int(r.headers["retry-after"]) >= 1
    # a different email is counted separately
    other = await make_student(db)
    assert (await login(client, other.email)).status_code == 200


# ---- tokens -----------------------------------------------------------------------------------------------------


async def test_me_requires_auth(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"
    assert r.headers["x-request-id"]


async def test_me_ok(client, db):
    user = await make_student(db)
    r = await client.get("/api/v1/auth/me", headers=auth_headers(user))
    assert r.status_code == 200
    assert r.json()["id"] == str(user.id)


async def test_access_expired_401_TOKEN_EXPIRED(client, db):
    user = await make_student(db)
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": str(user.id), "role": "STUDENT", "type": "access", "jti": "x", "iat": now - timedelta(hours=1), "exp": now - timedelta(minutes=1)},
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "TOKEN_EXPIRED"


async def test_garbage_and_wrong_type_tokens_401_TOKEN_INVALID(client, db):
    user = await make_student(db)
    r = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "TOKEN_INVALID"
    now = datetime.now(UTC)
    refresh_like = jwt.encode(
        {"sub": str(user.id), "type": "refresh", "exp": now + timedelta(minutes=5)}, settings.JWT_SECRET, algorithm="HS256"
    )
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh_like}"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "TOKEN_INVALID"
    wrong_secret = jwt.encode({"sub": str(user.id), "type": "access", "exp": now + timedelta(minutes=5)}, "x" * 40, algorithm="HS256")
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {wrong_secret}"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "TOKEN_INVALID"


async def test_deactivated_user_existing_token_rejected(client, db):
    user = await make_student(db)
    headers = auth_headers(user)
    user.is_active = False
    await db.flush()
    r = await client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "ACCOUNT_DEACTIVATED"


async def test_refresh_rotation(client, db):
    user = await make_student(db)
    first = await login(client, user.email)
    raw1 = refresh_cookie(first)

    r = await client.post("/api/v1/auth/refresh", headers=cookie_header(raw1))
    assert r.status_code == 200, r.text
    raw2 = refresh_cookie(r)
    assert raw2 != raw1
    assert r.json()["access_token"] and r.json()["user"]["id"] == str(user.id)

    old = (await db.execute(select(RefreshToken).where(RefreshToken.user_id == user.id).order_by(RefreshToken.created_at))).scalars().all()
    assert len(old) == 2
    assert old[0].revoked_at is not None and old[0].replaced_by_id == old[1].id
    assert old[1].revoked_at is None and old[0].family_id == old[1].family_id
    # tokens are stored hashed
    assert raw1 not in {t.token_hash for t in old} and len(old[0].token_hash) == 64


async def test_refresh_reuse_revokes_family(client, db):
    user = await make_student(db)
    raw1 = refresh_cookie(await login(client, user.email))
    raw2 = refresh_cookie(await client.post("/api/v1/auth/refresh", headers=cookie_header(raw1)))

    # replaying the rotated (revoked) token is treated as theft
    reuse = await client.post("/api/v1/auth/refresh", headers=cookie_header(raw1))
    assert reuse.status_code == 401
    assert reuse.json()["error"]["code"] == "TOKEN_REUSED"

    # ... and the legitimate newest token of the same family is now dead too
    after = await client.post("/api/v1/auth/refresh", headers=cookie_header(raw2))
    assert after.status_code == 401
    assert after.json()["error"]["code"] == "TOKEN_REUSED"
    live = (await db.execute(select(func.count()).select_from(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)))).scalar_one()
    assert live == 0


async def test_refresh_requires_csrf_header_and_allowed_origin(client, db):
    user = await make_student(db)
    raw = refresh_cookie(await login(client, user.email))
    r = await client.post("/api/v1/auth/refresh", headers={"Cookie": f"ch_refresh={raw}"})
    assert r.status_code == 403
    r = await client.post("/api/v1/auth/refresh", headers={**cookie_header(raw), "Origin": "http://evil.example"})
    assert r.status_code == 403
    r = await client.post("/api/v1/auth/refresh", headers={**cookie_header(raw), "Origin": "http://localhost:3000"})
    assert r.status_code == 200


async def test_refresh_missing_or_garbage_cookie_401(client):
    r = await client.post("/api/v1/auth/refresh", headers=CSRF)
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHENTICATED"
    r = await client.post("/api/v1/auth/refresh", headers=cookie_header("garbage-token"))
    assert r.status_code == 401 and r.json()["error"]["code"] == "TOKEN_INVALID"


async def test_refresh_for_deactivated_user_403(client, db):
    user = await make_student(db)
    raw = refresh_cookie(await login(client, user.email))
    user.is_active = False
    await db.flush()
    r = await client.post("/api/v1/auth/refresh", headers=cookie_header(raw))
    assert r.status_code == 403 and r.json()["error"]["code"] == "ACCOUNT_DEACTIVATED"


async def test_logout_revokes_family_and_clears_cookies(client, db):
    user = await make_student(db)
    raw1 = refresh_cookie(await login(client, user.email))
    raw2 = refresh_cookie(await client.post("/api/v1/auth/refresh", headers=cookie_header(raw1)))

    r = await client.post("/api/v1/auth/logout", headers=cookie_header(raw2))
    assert r.status_code == 204
    cleared = r.headers.get_list("set-cookie")
    assert any(c.startswith("ch_refresh=") and "Max-Age=0" in c for c in cleared)
    assert any(c.startswith("ch_role=") and "Max-Age=0" in c for c in cleared)

    after = await client.post("/api/v1/auth/refresh", headers=cookie_header(raw2))
    assert after.status_code == 401
    live = (await db.execute(select(func.count()).select_from(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)))).scalar_one()
    assert live == 0


async def test_logout_requires_csrf_header(client):
    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 403


# ---- password reset / change -----------------------------------------------------------------------------------


async def test_forgot_password_always_202(client, db, captured):
    user = await make_student(db)
    r1 = await client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    r2 = await client.post("/api/v1/auth/forgot-password", json={"email": "ghost@campushire.dev"})
    assert r1.status_code == r2.status_code == 202
    assert r1.json() == r2.json()
    assert len(captured.emails_to(user.email, "reset_password")) == 1
    assert captured.emails_to("ghost@campushire.dev") == []


async def test_forgot_password_rate_limited_after_3(client, db, enable_rate_limit):
    user = await make_student(db)
    for _ in range(3):
        assert (await client.post("/api/v1/auth/forgot-password", json={"email": user.email})).status_code == 202
    assert (await client.post("/api/v1/auth/forgot-password", json={"email": user.email})).status_code == 429


async def test_reset_password_flow_revokes_refresh_tokens(client, db, captured):
    user = await make_student(db)
    raw_refresh = refresh_cookie(await login(client, user.email))
    await client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    token = captured.emails_to(user.email, "reset_password")[0]["context"]["reset_url"].split("token=")[1]

    weak = await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "weak"})
    assert weak.status_code == 422

    r = await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "Brand!New9pw"})
    assert r.status_code == 200, r.text
    assert (await login(client, user.email, DEFAULT_PASSWORD)).status_code == 401
    assert (await login(client, user.email, "Brand!New9pw")).status_code == 200
    # old refresh token no longer works
    assert (await client.post("/api/v1/auth/refresh", headers=cookie_header(raw_refresh))).status_code == 401
    # single use
    again = await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "Another!Pw99"})
    assert again.status_code == 400


async def test_change_password(client, db):
    user = await make_student(db)
    headers = auth_headers(user)
    wrong = await client.post("/api/v1/auth/change-password", headers=headers, json={"current_password": "Nope!Nope1", "new_password": "Brand!New9pw"})
    assert wrong.status_code == 422
    same = await client.post("/api/v1/auth/change-password", headers=headers, json={"current_password": DEFAULT_PASSWORD, "new_password": DEFAULT_PASSWORD})
    assert same.status_code == 422
    ok = await client.post("/api/v1/auth/change-password", headers=headers, json={"current_password": DEFAULT_PASSWORD, "new_password": "Brand!New9pw"})
    assert ok.status_code == 200
    assert (await login(client, user.email, "Brand!New9pw")).status_code == 200


async def test_validation_error_envelope_shape(client):
    r = await client.post("/api/v1/auth/login", json={})
    assert r.status_code == 422
    err = r.json()["error"]
    assert set(err) >= {"code", "message", "details", "request_id"}
    assert {d["field"] for d in err["details"]} == {"email", "password"}


async def test_unknown_route_uses_envelope(client):
    r = await client.get("/api/v1/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


async def test_security_headers_and_health(client):
    r = await client.get("/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    ready = await client.get("/readyz")
    assert ready.status_code == 200 and ready.json()["checks"] == {"db": "ok", "redis": "ok"}


async def test_cors_allows_frontend_origin_with_credentials(client):
    r = await client.options(
        "/api/v1/auth/login",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"},
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert r.headers["access-control-allow-credentials"] == "true"


async def test_metrics_are_recorded_in_redis(client):
    from app.core import redis as redis_core

    await client.get("/api/v1/auth/me")
    keys = [k async for k in redis_core.get_redis().scan_iter("metrics:*")]
    assert len(keys) >= 1
    h = await redis_core.get_redis().hgetall(keys[0])
    assert int(h["count"]) >= 1
