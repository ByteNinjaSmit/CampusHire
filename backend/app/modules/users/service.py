import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import utcnow
from app.core.errors import AppError, bad_request, not_found, unprocessable
from app.core.pagination import PageParams, paginate
from app.core.security import hash_password
from app.core.side_effects import audit, notify
from app.modules.auth.emails import send_verification_email
from app.modules.companies.models import CompanyMember
from app.modules.faculty.models import Faculty
from app.modules.students.models import Student
from app.modules.users import repository as repo
from app.modules.users import schemas as s
from app.modules.users.models import User

# ---- builders -----------------------------------------------------------------------------------------


async def _student_profile(session: AsyncSession, student: Student) -> s.StudentProfile:
    resume = await repo.get_document(session, student.default_resume_id) if student.default_resume_id else None
    return s.StudentProfile(
        user_id=student.user_id,
        department=student.department,
        gpa=student.gpa,
        enrollment_no=student.enrollment_no,
        graduation_year=student.graduation_year,
        skills=list(student.skills or []),
        bio=student.bio,
        linkedin_url=student.linkedin_url,
        github_url=student.github_url,
        portfolio_url=student.portfolio_url,
        default_resume=s.DocumentSummary.model_validate(resume) if resume else None,
    )


async def _profiles(session: AsyncSession, user: User) -> dict[str, Any]:
    out: dict[str, Any] = {"student": None, "faculty": None, "company": None}
    if user.role == "STUDENT":
        st = await repo.get_student(session, user.id)
        if st:
            out["student"] = await _student_profile(session, st)
    elif user.role == "FACULTY":
        fa = await repo.get_faculty(session, user.id)
        if fa:
            out["faculty"] = s.FacultyProfile.model_validate(fa)
    elif user.role == "COMPANY":
        m = await repo.get_company_membership(session, user.id)
        if m:
            member, company = m
            out["company"] = s.CompanyMembership(
                company_id=company.id,
                company_name=company.name,
                company_status=company.status,
                job_title=member.job_title,
            )
    return out


async def build_me(session: AsyncSession, user: User) -> s.Me:
    return s.Me(
        id=user.id,
        email=user.email,
        role=user.role,  # type: ignore[arg-type]  # str validated by pydantic into the Role enum
        full_name=user.full_name,
        phone=user.phone,
        avatar_url=user.avatar_url,
        email_verified=user.email_verified_at is not None,
        is_active=user.is_active,
        created_at=user.created_at,
        **await _profiles(session, user),
    )


async def build_detail(session: AsyncSession, user: User) -> s.UserDetail:
    base = s.UserSummary.model_validate(user, from_attributes=True)
    return s.UserDetail(
        **base.model_dump(),
        avatar_url=user.avatar_url,
        deactivated_at=user.deactivated_at,
        deactivated_reason=user.deactivated_reason,
        **await _profiles(session, user),
    )


def summary_of(user: User) -> s.UserSummary:
    return s.UserSummary(
        id=user.id,
        email=user.email,
        role=user.role,  # type: ignore[arg-type]  # validated into the Role enum
        full_name=user.full_name,
        phone=user.phone,
        is_active=user.is_active,
        email_verified=user.email_verified_at is not None,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


# ---- queries --------------------------------------------------------------------------------------------


async def list_users(
    session: AsyncSession, params: PageParams, role: str | None, q: str | None, is_active: bool | None
) -> dict[str, Any]:
    rows, total = await paginate(session, repo.list_query(role, q, is_active), params)
    from app.core.pagination import make_page

    return make_page([summary_of(u) for u in rows], total, params)


async def get_user_or_404(session: AsyncSession, user_id: uuid.UUID) -> User:
    user = await repo.get_by_id(session, user_id)
    if user is None:
        raise not_found("User not found")
    return user


# ---- commands ---------------------------------------------------------------------------------------------


async def create_user(session: AsyncSession, admin: User, data: s.AdminCreateUserRequest) -> User:
    role = data.role.value
    missing = {"STUDENT": data.student, "FACULTY": data.faculty, "COMPANY": data.company}
    if role in missing and missing[role] is None:
        raise unprocessable(
            f"A '{role.lower()}' profile block is required for role {role}",
            details=[{"field": role.lower(), "message": "This field is required for the selected role"}],
        )
    company = None
    if role == "COMPANY":
        assert data.company is not None
        company = await repo.get_company(session, data.company.company_id)
        if company is None:
            raise unprocessable(
                "Company not found",
                details=[{"field": "company.company_id", "message": "Company not found"}],
            )

    user = User(
        id=uuid.uuid4(),
        email=data.email,
        password_hash=hash_password(data.password),
        role=role,
        full_name=data.full_name,
        phone=data.phone,
        email_verified_at=utcnow() if data.mark_verified else None,
    )
    session.add(user)
    await session.flush()  # surfaces uq_users_email -> DUPLICATE_EMAIL

    if role == "STUDENT":
        assert data.student is not None
        session.add(
            Student(
                user_id=user.id,
                department=data.student.department,
                gpa=data.student.gpa,
                enrollment_no=data.student.enrollment_no,
                graduation_year=data.student.graduation_year,
                skills=[],
            )
        )
    elif role == "FACULTY":
        assert data.faculty is not None
        session.add(
            Faculty(
                user_id=user.id,
                department=data.faculty.department,
                designation=data.faculty.designation,
                employee_id=data.faculty.employee_id,
            )
        )
    elif role == "COMPANY":
        assert data.company is not None and company is not None
        session.add(CompanyMember(user_id=user.id, company_id=company.id, job_title=data.company.job_title))
    await session.flush()

    if not data.mark_verified:
        await send_verification_email(session, user)
    audit(session, admin, "user.create", "user", user.id, after={"email": user.email, "role": role})
    return user


async def update_user(session: AsyncSession, admin: User, user_id: uuid.UUID, data: s.UpdateUserRequest) -> User:
    user = await get_user_or_404(session, user_id)
    before = {"full_name": user.full_name, "phone": user.phone}
    fields = data.model_fields_set
    if "full_name" in fields and data.full_name is not None:
        user.full_name = data.full_name
    if "phone" in fields:
        user.phone = data.phone

    if data.student is not None:
        if user.role != "STUDENT":
            raise bad_request("Student fields can only be set on a STUDENT user")
        st = await repo.get_student(session, user.id)
        if st is None:
            raise not_found("Student profile not found")
        for k in data.student.model_fields_set:
            v = getattr(data.student, k)
            if k in ("department", "gpa") and v is None:
                continue  # NOT NULL columns
            setattr(st, k, v)
    if data.faculty is not None:
        if user.role != "FACULTY":
            raise bad_request("Faculty fields can only be set on a FACULTY user")
        fa = await repo.get_faculty(session, user.id)
        if fa is None:
            raise not_found("Faculty profile not found")
        for k in data.faculty.model_fields_set:
            v = getattr(data.faculty, k)
            if k == "department" and v is None:
                continue
            setattr(fa, k, v)
    await session.flush()
    audit(
        session,
        admin,
        "user.update",
        "user",
        user.id,
        before=before,
        after={"full_name": user.full_name, "phone": user.phone},
    )
    return user


async def update_me(session: AsyncSession, user: User, data: s.UpdateMeRequest) -> User:
    before = {"full_name": user.full_name, "phone": user.phone, "avatar_url": user.avatar_url}
    fields = data.model_fields_set
    if "full_name" in fields and data.full_name is not None:
        user.full_name = data.full_name
    if "phone" in fields:
        user.phone = data.phone
    if "avatar_url" in fields:
        user.avatar_url = data.avatar_url
    await session.flush()
    audit(
        session,
        user,
        "user.update_self",
        "user",
        user.id,
        before=before,
        after={"full_name": user.full_name, "phone": user.phone, "avatar_url": user.avatar_url},
    )
    return user


async def deactivate_user(session: AsyncSession, admin: User, user_id: uuid.UUID, reason: str) -> User:
    if user_id == admin.id:
        raise bad_request("You cannot deactivate your own account", "BAD_REQUEST")
    user = await get_user_or_404(session, user_id)
    if not user.is_active:
        return user
    user.is_active = False
    user.deactivated_at = utcnow()
    user.deactivated_reason = reason
    await repo.revoke_all_refresh_tokens(session, user.id)
    await session.flush()
    audit(session, admin, "user.deactivate", "user", user.id, after={"reason": reason})
    return user


async def activate_user(session: AsyncSession, admin: User, user_id: uuid.UUID) -> User:
    user = await get_user_or_404(session, user_id)
    if user.is_active:
        return user
    user.is_active = True
    user.deactivated_at = None
    user.deactivated_reason = None
    await session.flush()
    audit(session, admin, "user.activate", "user", user.id)
    notify(session, user.id, "SYSTEM", "Account reactivated", "Your CampusHire account has been reactivated.")
    return user


async def bulk_action(session: AsyncSession, admin: User, data: s.BulkUserAction) -> s.BulkActionResult:
    updated: list[uuid.UUID] = []
    failed: list[s.BulkFailure] = []
    for uid in dict.fromkeys(data.ids):  # de-duplicate, keep order
        try:
            async with session.begin_nested():
                if data.action == "deactivate":
                    await deactivate_user(session, admin, uid, data.reason or "Deactivated by administrator")
                else:
                    await activate_user(session, admin, uid)
            updated.append(uid)
        except AppError as exc:
            failed.append(s.BulkFailure(id=uid, code=exc.code, message=exc.message))
    return s.BulkActionResult(updated=updated, failed=failed)
