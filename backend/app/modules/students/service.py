"""Student profiles (spec section 3): profile CRUD, staff visibility scoping, deactivate, application history."""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.core.pagination import PageParams, make_page, paginate
from app.core.permissions import owned_internship_ids
from app.core.side_effects import audit
from app.core.storage import Storage
from app.core.types import ApplicationStatus
from app.modules.auth.schemas import MessageResponse
from app.modules.companies.service import logo_url_map
from app.modules.documents import service as documents_service
from app.modules.students import repository as repo
from app.modules.students import schemas as s
from app.modules.students.models import Student
from app.modules.users import service as users_service
from app.modules.users.models import User
from app.modules.users.schemas import DocumentSummary


# ---- builders ------------------------------------------------------------------------------------------------
async def _profile(session: AsyncSession, student: Student) -> s.StudentProfile:
    resume = await repo.get_document(session, student.default_resume_id)
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
        default_resume=DocumentSummary.model_validate(resume) if resume else None,
    )


async def _stats(session: AsyncSession, student_id: uuid.UUID, scope: Select[Any] | None) -> s.StudentStats:
    counts = await repo.status_counts(session, student_id, scope)
    by_status = {st: counts.get(st.value, 0) for st in ApplicationStatus}
    return s.StudentStats(
        total_applications=sum(by_status.values()),
        by_status=by_status,
        interviews_upcoming=await repo.upcoming_interviews(session, student_id, scope),
    )


def _item(student: Student, user: User, application_count: int, placed: bool) -> s.StudentListItem:
    return s.StudentListItem(
        user_id=student.user_id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        department=student.department,
        gpa=student.gpa,
        is_active=user.is_active,
        application_count=application_count,
        placed=placed,
    )


async def _me(session: AsyncSession, student: Student, user: User) -> s.StudentMe:
    profile = await _profile(session, student)
    return s.StudentMe(
        **profile.model_dump(),
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        stats=await _stats(session, student.user_id, None),
    )


def _snap(student: Student, user: User) -> dict[str, Any]:
    def conv(v: Any) -> Any:
        return float(v) if isinstance(v, Decimal) else v

    return {
        k: conv(v)
        for k, v in {
            "full_name": user.full_name,
            "phone": user.phone,
            "department": student.department,
            "gpa": student.gpa,
            "enrollment_no": student.enrollment_no,
            "graduation_year": student.graduation_year,
            "skills": list(student.skills or []),
            "bio": student.bio,
            "linkedin_url": student.linkedin_url,
            "github_url": student.github_url,
            "portfolio_url": student.portfolio_url,
            "default_resume_id": str(student.default_resume_id) if student.default_resume_id else None,
        }.items()
    }


async def _staff_scope(session: AsyncSession, viewer: User) -> Select[Any] | None:
    """None for ADMIN (no restriction), else the internship ids the staff user owns."""
    return None if viewer.role == "ADMIN" else await owned_internship_ids(session, viewer)


# ---- own profile ------------------------------------------------------------------------------------------------
async def _own(session: AsyncSession, user: User) -> tuple[Student, User]:
    row = await repo.get_with_user(session, user.id)
    if row is None:
        raise not_found("Student profile not found")
    return row


async def get_me(session: AsyncSession, user: User) -> s.StudentMe:
    student, u = await _own(session, user)
    return await _me(session, student, u)


def _apply_update(student: Student, user: User, data: s.StudentProfileUpdate) -> None:
    for field in data.model_fields_set:
        value = getattr(data, field)
        if field == "phone":
            user.phone = value
        elif field == "full_name":
            if value is not None:
                user.full_name = value
        elif field in ("department", "gpa"):
            if value is not None:  # NOT NULL columns: ignore explicit null
                setattr(student, field, value)
        elif field == "skills":
            student.skills = list(value or [])
        else:
            setattr(student, field, value)


async def update_me(session: AsyncSession, user: User, data: s.StudentProfileUpdate) -> s.StudentMe:
    student, u = await _own(session, user)
    before = _snap(student, u)
    _apply_update(student, u, data)
    await session.flush()  # DB CHECKs (gpa, graduation_year, bio, phone) -> 422 via IntegrityError mapping
    audit(session, user, "student.update_profile", "student", student.user_id, before=before, after=_snap(student, u))
    return await _me(session, student, u)


async def set_default_resume(session: AsyncSession, user: User, document_id: uuid.UUID) -> s.StudentMe:
    student, u = await _own(session, user)
    doc = await documents_service.validate_resume_document(session, user.id, document_id)
    before = {"default_resume_id": str(student.default_resume_id) if student.default_resume_id else None}
    student.default_resume_id = doc.id
    await session.flush()
    audit(session, user, "student.set_default_resume", "student", student.user_id, before=before, after={"default_resume_id": str(doc.id)})
    return await _me(session, student, u)


# ---- staff / admin ------------------------------------------------------------------------------------------------
async def list_students(
    session: AsyncSession,
    viewer: User,
    params: PageParams,
    q: str | None,
    department: str | None,
    gpa_min: float | None,
    gpa_max: float | None,
) -> dict[str, Any]:
    scope = await _staff_scope(session, viewer)
    stmt = repo.list_query(q, department, gpa_min, gpa_max, scope)
    rows, total = await paginate(session, stmt, params, scalars=False)
    return make_page([_item(r[0], r[1], int(r[2]), bool(r[3])) for r in rows], total, params)


async def _visible_item(
    session: AsyncSession, viewer: User, student_id: uuid.UUID
) -> tuple[Student, User, int, bool, Select[Any] | None]:
    scope = await _staff_scope(session, viewer)
    if scope is not None and not await repo.has_application_in_scope(session, student_id, scope):
        raise not_found("Student not found")
    row = await repo.item_row(session, student_id, scope)
    if row is None:
        raise not_found("Student not found")
    return row[0], row[1], row[2], row[3], scope


async def _detail(session: AsyncSession, student: Student, user: User, count: int, placed: bool, scope: Select[Any] | None) -> s.StudentDetail:
    item = _item(student, user, count, placed)
    return s.StudentDetail(
        **item.model_dump(),
        profile=await _profile(session, student),
        stats=await _stats(session, student.user_id, scope),
    )


async def get_student(session: AsyncSession, viewer: User, student_id: uuid.UUID) -> s.StudentDetail:
    student, user, count, placed, scope = await _visible_item(session, viewer, student_id)
    return await _detail(session, student, user, count, placed, scope)


async def admin_update(
    session: AsyncSession, admin: User, student_id: uuid.UUID, data: s.AdminStudentUpdate
) -> s.StudentDetail:
    row = await repo.get_with_user(session, student_id)
    if row is None:
        raise not_found("Student not found")
    student, user = row
    before = _snap(student, user)
    _apply_update(student, user, data)
    await session.flush()
    audit(session, admin, "student.update", "student", student.user_id, before=before, after=_snap(student, user))
    student, user, count, placed, scope = await _visible_item(session, admin, student_id)
    return await _detail(session, student, user, count, placed, scope)


async def deactivate(session: AsyncSession, admin: User, student_id: uuid.UUID, reason: str) -> MessageResponse:
    row = await repo.get_with_user(session, student_id)
    if row is None:
        raise not_found("Student not found")
    await users_service.deactivate_user(session, admin, student_id, reason)
    audit(session, admin, "student.deactivate", "student", student_id, after={"reason": reason})
    return MessageResponse(message="Student account deactivated")


async def application_history(
    session: AsyncSession, storage: Storage, viewer: User, student_id: uuid.UUID, params: PageParams
) -> dict[str, Any]:
    if viewer.role == "STUDENT" and viewer.id != student_id:
        raise not_found("Student not found")
    if await repo.get_with_user(session, student_id) is None:
        raise not_found("Student not found")
    stmt = repo.history_query(student_id, shared_only=viewer.role == "STUDENT")
    rows, total = await paginate(session, stmt, params, scalars=False)
    logos = await logo_url_map(session, storage, [r[2].logo_document_id for r in rows])
    items = []
    for app, internship, company, student, user, next_interview_at, eval_avg in rows:
        items.append(
            s.ApplicationSummary(
                id=app.id,
                status=app.status,  # type: ignore[arg-type]  # validated into ApplicationStatus
                status_changed_at=app.status_changed_at,
                created_at=app.created_at,
                internship=s.AppInternshipRef(
                    id=internship.id,
                    title=internship.title,
                    company_id=company.id,
                    company_name=company.name,
                    company_logo_url=logos.get(company.logo_document_id) if company.logo_document_id else None,
                    application_deadline=internship.application_deadline,
                    start_date=internship.start_date,
                ),
                student=s.AppStudentRef(
                    id=user.id,
                    full_name=user.full_name,
                    email=user.email,
                    department=student.department,
                    gpa=student.gpa,
                ),
                next_interview_at=next_interview_at,
                evaluation_avg=round(float(eval_avg), 2) if eval_avg is not None else None,
            )
        )
    return make_page(items, total, params)
