import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import utcnow
from app.core.config import settings
from app.core.deps import ClientInfo
from app.core.errors import AppError, bad_request, unauthenticated
from app.core.security import (
    create_access_token,
    fake_verify,
    hash_password,
    hash_token,
    needs_rehash,
    verify_password,
)
from app.core.side_effects import audit, notify
from app.modules.auth import repository as repo
from app.modules.auth.models import RefreshToken
from app.modules.auth.emails import send_reset_email, send_verification_email
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    CompanyRegisterRequest,
    LoginRequest,
    StudentRegisterRequest,
    TokenResponse,
)
from app.modules.companies.models import Company, CompanyMember
from app.modules.students.models import Student
from app.modules.users import repository as users_repo
from app.modules.users.models import User
from app.modules.users.service import build_me


@dataclass
class AuthResult:
    token: TokenResponse
    refresh_token: str
    role: str


# ---- registration -------------------------------------------------------------------------------------


async def register_student(session: AsyncSession, data: StudentRegisterRequest) -> None:
    user = User(
        id=uuid.uuid4(),
        email=data.email,
        password_hash=hash_password(data.password),
        role="STUDENT",
        full_name=data.full_name,
        phone=data.phone,
    )
    session.add(user)
    await session.flush()  # uq_users_email -> 409 DUPLICATE_EMAIL
    session.add(
        Student(
            user_id=user.id,
            department=data.department,
            gpa=data.gpa,
            enrollment_no=data.enrollment_no,
            graduation_year=data.graduation_year,
            skills=[],
        )
    )
    await session.flush()
    await send_verification_email(session, user)
    audit(session, user, "user.register", "user", user.id, after={"email": user.email, "role": "STUDENT"})


async def register_company(session: AsyncSession, data: CompanyRegisterRequest) -> None:
    user = User(
        id=uuid.uuid4(),
        email=data.email,
        password_hash=hash_password(data.password),
        role="COMPANY",
        full_name=data.full_name,
        phone=data.phone,
    )
    session.add(user)
    await session.flush()
    c = data.company
    company = Company(
        id=uuid.uuid4(),
        name=c.name,
        registration_number=c.registration_number,
        industry=c.industry,
        location=c.location,
        website=c.website,
        contact_person_name=c.contact_person_name,
        contact_email=c.contact_email,
        contact_phone=c.contact_phone,
        status="PENDING",
        created_by=user.id,
    )
    session.add(company)
    await session.flush()  # uq_companies_registration_number -> 409 DUPLICATE_REGISTRATION_NUMBER
    session.add(CompanyMember(user_id=user.id, company_id=company.id, job_title=data.job_title))
    await session.flush()
    await send_verification_email(session, user)
    audit(session, user, "user.register", "user", user.id, after={"email": user.email, "role": "COMPANY"})
    audit(session, user, "company.register", "company", company.id, after={"name": company.name, "status": "PENDING"})
    for admin_id in await users_repo.active_admin_ids(session):
        notify(
            session,
            admin_id,
            "COMPANY_REGISTERED",
            "New company awaiting approval",
            f"{company.name} registered and is waiting for approval.",
            link="/admin/companies",
            data={"company_id": str(company.id)},
        )


# ---- login / refresh / logout ---------------------------------------------------------------------------


async def _fail_login(
    session: AsyncSession, email: str, user: User | None, client: ClientInfo, code: str, message: str, status: int
) -> AppError:
    """Persist the failed attempt (commit before raising, since an error response rolls the request back)."""
    repo.add_login_event(
        session, user_id=user.id if user else None, email=email, success=False, ip=client.ip, user_agent=client.user_agent
    )
    await session.commit()
    if status == 401:
        return unauthenticated(message, code)
    return AppError(status, code, message)


def _issue_tokens(
    session: AsyncSession, user: User, client: ClientInfo, family_id: uuid.UUID | None = None
) -> tuple[str, str, int, RefreshToken]:
    row, raw = repo.new_refresh_token(
        user.id, family_id or uuid.uuid4(), settings.REFRESH_TTL_DAYS, client.ip, client.user_agent
    )
    session.add(row)
    access, expires_in = create_access_token(user.id, user.role)
    return access, raw, expires_in, row


async def login(session: AsyncSession, data: LoginRequest, client: ClientInfo) -> AuthResult:
    user = await users_repo.get_by_email(session, data.email)
    if user is None:
        fake_verify(data.password)
        raise await _fail_login(session, data.email, None, client, "INVALID_CREDENTIALS", "Invalid email or password", 401)
    if not verify_password(user.password_hash, data.password):
        raise await _fail_login(session, data.email, user, client, "INVALID_CREDENTIALS", "Invalid email or password", 401)
    if not user.is_active:
        raise await _fail_login(session, data.email, user, client, "ACCOUNT_DEACTIVATED", "This account has been deactivated", 403)
    if user.email_verified_at is None:
        raise await _fail_login(
            session, data.email, user, client, "EMAIL_NOT_VERIFIED", "Please verify your email address before signing in", 403
        )

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)
    user.last_login_at = utcnow()
    access, raw, expires_in, _ = _issue_tokens(session, user, client)
    repo.add_login_event(session, user_id=user.id, email=user.email, success=True, ip=client.ip, user_agent=client.user_agent)
    audit(session, user, "auth.login", "user", user.id)
    await session.flush()
    me = await build_me(session, user)
    return AuthResult(TokenResponse(access_token=access, expires_in=expires_in, user=me), raw, user.role)


async def refresh(session: AsyncSession, raw_token: str | None, client: ClientInfo) -> AuthResult:
    if not raw_token:
        raise unauthenticated("Missing refresh token")
    row = await repo.get_refresh_by_hash(session, hash_token(raw_token))
    if row is None:
        raise unauthenticated("Invalid refresh token", "TOKEN_INVALID")
    if row.revoked_at is not None:
        # Reuse of a rotated/revoked token => assume theft: kill the whole family. Commit before raising.
        await repo.revoke_family(session, row.family_id)
        audit(session, row.user_id, "auth.refresh_reuse", "user", row.user_id)
        await session.commit()
        raise unauthenticated("Refresh token reuse detected; please sign in again", "TOKEN_REUSED")
    if row.expires_at <= utcnow():
        raise unauthenticated("Refresh token expired", "TOKEN_INVALID")
    user = await users_repo.get_by_id(session, row.user_id)
    if user is None:
        raise unauthenticated("Invalid refresh token", "TOKEN_INVALID")
    if not user.is_active:
        raise AppError(403, "ACCOUNT_DEACTIVATED", "This account has been deactivated")

    access, new_raw, expires_in, new_row = _issue_tokens(session, user, client, family_id=row.family_id)
    row.revoked_at = utcnow()
    row.replaced_by_id = new_row.id
    await session.flush()
    me = await build_me(session, user)
    return AuthResult(TokenResponse(access_token=access, expires_in=expires_in, user=me), new_raw, user.role)


async def logout(session: AsyncSession, raw_token: str | None) -> None:
    if not raw_token:
        return
    row = await repo.get_refresh_by_hash(session, hash_token(raw_token))
    if row is not None:
        await repo.revoke_family(session, row.family_id)
        audit(session, row.user_id, "auth.logout", "user", row.user_id)


# ---- e-mail verification / password reset --------------------------------------------------------------------


async def verify_email(session: AsyncSession, raw_token: str) -> str:
    tok = await repo.get_user_token(session, raw_token, "VERIFY_EMAIL")
    if tok is None:
        raise bad_request("Invalid or expired verification link")
    user = await users_repo.get_by_id(session, tok.user_id)
    if user is None:
        raise bad_request("Invalid or expired verification link")
    if user.email_verified_at is not None:
        return "Email already verified"
    if not repo.token_is_live(tok):
        raise bad_request("Invalid or expired verification link")
    tok.used_at = utcnow()
    user.email_verified_at = utcnow()
    audit(session, user, "user.verify_email", "user", user.id)
    return "Email verified. You can now sign in."


async def resend_verification(session: AsyncSession, email: str) -> None:
    user = await users_repo.get_by_email(session, email)
    if user is not None and user.email_verified_at is None and user.is_active:
        await send_verification_email(session, user)


async def forgot_password(session: AsyncSession, email: str) -> None:
    user = await users_repo.get_by_email(session, email)
    if user is not None and user.is_active:
        await send_reset_email(session, user)


async def reset_password(session: AsyncSession, raw_token: str, new_password: str) -> None:
    tok = await repo.get_user_token(session, raw_token, "RESET_PASSWORD")
    if tok is None or not repo.token_is_live(tok):
        raise bad_request("Invalid or expired reset link")
    user = await users_repo.get_by_id(session, tok.user_id)
    if user is None:
        raise bad_request("Invalid or expired reset link")
    user.password_hash = hash_password(new_password)
    if user.email_verified_at is None:
        user.email_verified_at = utcnow()  # the reset link proves control of the mailbox
    tok.used_at = utcnow()
    await repo.revoke_user_tokens(session, user.id)
    audit(session, user, "auth.reset_password", "user", user.id)


async def change_password(
    session: AsyncSession, user: User, data: ChangePasswordRequest, current_raw_refresh: str | None
) -> None:
    if not verify_password(user.password_hash, data.current_password):
        raise AppError(
            422,
            "VALIDATION_ERROR",
            "Current password is incorrect",
            [{"field": "current_password", "message": "Current password is incorrect"}],
        )
    if data.current_password == data.new_password:
        raise AppError(
            422,
            "VALIDATION_ERROR",
            "New password must be different from the current password",
            [{"field": "new_password", "message": "New password must be different from the current password"}],
        )
    user.password_hash = hash_password(data.new_password)
    keep_family = None
    if current_raw_refresh:
        row = await repo.get_refresh_by_hash(session, hash_token(current_raw_refresh))
        if row is not None and row.user_id == user.id:
            keep_family = row.family_id
    await repo.revoke_user_tokens(session, user.id, except_family=keep_family)
    audit(session, user, "auth.change_password", "user", user.id)
