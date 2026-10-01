"""Test data factories (plan 9.1). Every factory takes the test ``session`` first and flushes (no commit)."""

import itertools
import random
import string
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import utcnow
from app.core.security import create_access_token, hash_password
from app.modules.applications.models import Application, ApplicationStatusHistory
from app.modules.companies.models import Company, CompanyMember
from app.modules.documents.models import Document
from app.modules.faculty.models import Faculty
from app.modules.internships.models import Internship
from app.modules.students.models import Student
from app.modules.users.models import User

DEFAULT_PASSWORD = "Passw0rd!x"
_DEFAULT_HASH = hash_password(DEFAULT_PASSWORD)  # hash once: argon2 is deliberately slow
_counter = itertools.count(1)


def _n() -> int:
    return next(_counter)


def _rand(chars: str, k: int) -> str:
    return "".join(random.choices(chars, k=k))


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}{_n()}.{_rand(string.ascii_lowercase, 5)}@campushire.dev"


def unique_cin() -> str:
    """Valid Indian CIN: U + 5 digits + 2 letters + 4 digits + 3 letters + 6 digits."""
    return f"U{_rand(string.digits, 5)}KA{_rand(string.digits, 4)}PTC{_rand(string.digits, 6)}"


def auth_headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user.id, user.role)
    return {"Authorization": f"Bearer {token}"}


async def make_user(
    session: AsyncSession,
    role: str = "STUDENT",
    verified: bool = True,
    *,
    email: str | None = None,
    password: str | None = None,
    full_name: str | None = None,
    phone: str | None = None,
    is_active: bool = True,
    **extra: Any,
) -> User:
    user = User(
        id=uuid.uuid4(),
        email=(email or unique_email(role.lower())).lower(),
        password_hash=_DEFAULT_HASH if password is None else hash_password(password),
        role=role,
        full_name=full_name or f"Test {role.title()} {_n()}",
        phone=phone,
        is_active=is_active,
        email_verified_at=utcnow() if verified else None,
        **extra,
    )
    session.add(user)
    await session.flush()
    return user


async def make_admin(session: AsyncSession, **kw: Any) -> User:
    return await make_user(session, "ADMIN", **kw)


async def make_student(
    session: AsyncSession,
    verified: bool = True,
    *,
    department: str = "CSE",
    gpa: Decimal | float | str = "3.50",
    enrollment_no: str | None = None,
    **kw: Any,
) -> User:
    """Returns the User; the Student row is available as ``user.profile``."""
    user = await make_user(session, "STUDENT", verified, **kw)
    student = Student(user_id=user.id, department=department, gpa=Decimal(str(gpa)), enrollment_no=enrollment_no, skills=[])
    session.add(student)
    await session.flush()
    user.profile = student  # type: ignore[attr-defined]  # plain python attribute for test convenience
    return user


async def make_faculty(session: AsyncSession, verified: bool = True, *, department: str = "CSE", **kw: Any) -> User:
    user = await make_user(session, "FACULTY", verified, **kw)
    fac = Faculty(user_id=user.id, department=department, designation="Professor")
    session.add(fac)
    await session.flush()
    user.profile = fac  # type: ignore[attr-defined]  # plain python attribute for test convenience
    return user


async def make_company(
    session: AsyncSession,
    *,
    name: str | None = None,
    status: str = "ACTIVE",
    created_by: User | None = None,
    **kw: Any,
) -> Company:
    company = Company(
        id=uuid.uuid4(),
        name=name or f"Company {_n()}",
        registration_number=kw.pop("registration_number", None) or unique_cin(),
        location=kw.pop("location", "Bengaluru, India"),
        industry=kw.pop("industry", "Software"),
        contact_person_name=kw.pop("contact_person_name", "Contact Person"),
        contact_email=kw.pop("contact_email", unique_email("contact")),
        status=status,
        created_by=created_by.id if created_by else None,
        **kw,
    )
    session.add(company)
    await session.flush()
    return company


async def make_company_user(
    session: AsyncSession, company: Company | None = None, verified: bool = True, **kw: Any
) -> User:
    """COMPANY user that is a member of ``company`` (created when omitted). ``user.company`` is the Company."""
    user = await make_user(session, "COMPANY", verified, **kw)
    company = company or await make_company(session, created_by=user)
    session.add(CompanyMember(user_id=user.id, company_id=company.id, job_title="Recruiter"))
    await session.flush()
    user.company = company  # type: ignore[attr-defined]  # plain python attribute for test convenience
    return user


async def make_internship(
    session: AsyncSession,
    owner: User,
    *,
    company: Company | None = None,
    status: str = "APPROVED",
    deadline_in_days: int = 20,
    weeks: int = 12,
    **kw: Any,
) -> Internship:
    """Valid internship satisfying every DB CHECK. Service-level future-date rules are bypassed on purpose,
    so pass a negative ``deadline_in_days`` to create an expired posting."""
    company = company or await make_company(session, created_by=owner)
    deadline = datetime.now(UTC) + timedelta(days=deadline_in_days)
    start = (deadline + timedelta(days=10)).date()
    end = start + timedelta(weeks=weeks)
    internship = Internship(
        id=uuid.uuid4(),
        company_id=company.id,
        posted_by=owner.id,
        title=kw.pop("title", f"Software Engineering Intern {_n()}"),
        description=kw.pop("description", "Work on real products with an experienced team and learn modern tooling."),
        domain=kw.pop("domain", "Software Engineering"),
        location=kw.pop("location", "Bengaluru"),
        work_mode=kw.pop("work_mode", "HYBRID"),
        stipend_monthly=Decimal(str(kw.pop("stipend_monthly", 20000))),
        duration_weeks=weeks,
        start_date=kw.pop("start_date", start),
        end_date=kw.pop("end_date", end),
        application_deadline=kw.pop("application_deadline", deadline),
        openings=kw.pop("openings", 2),
        skills=kw.pop("skills", ["Python"]),
        status=status,
        approved_by=owner.id if status in ("APPROVED", "CLOSED") else None,
        approved_at=utcnow() if status in ("APPROVED", "CLOSED") else None,
        **kw,
    )
    session.add(internship)
    await session.flush()
    return internship


async def make_resume(
    session: AsyncSession,
    owner: User,
    *,
    status: str = "UPLOADED",
    verification_status: str = "PENDING",
    size_bytes: int = 120_000,
    filename: str = "resume.pdf",
) -> Document:
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        owner_id=owner.id,
        kind="RESUME",
        bucket="resumes",
        object_key=f"{owner.id}/{doc_id}/{filename}",
        filename=filename,
        content_type="application/pdf",
        size_bytes=size_bytes,
        status=status,
        verification_status=verification_status,
    )
    session.add(doc)
    await session.flush()
    return doc


async def make_application(
    session: AsyncSession,
    student: User,
    internship: Internship,
    *,
    resume: Document | None = None,
    status: str = "PENDING",
    **kw: Any,
) -> Application:
    resume = resume or await make_resume(session, student)
    app = Application(
        id=uuid.uuid4(),
        internship_id=internship.id,
        student_id=student.id,
        resume_document_id=resume.id,
        cover_letter=kw.pop("cover_letter", "I am excited to apply for this internship and contribute to the team. " * 2),
        qualifications=kw.pop("qualifications", "Strong coursework in algorithms and software engineering."),
        answers=kw.pop("answers", {}),
        status=status,
        **kw,
    )
    session.add(app)
    await session.flush()
    session.add(ApplicationStatusHistory(application_id=app.id, from_status=None, to_status="PENDING", changed_by=student.id))
    if status != "PENDING":
        session.add(
            ApplicationStatusHistory(application_id=app.id, from_status="PENDING", to_status=status, changed_by=None)
        )
    await session.flush()
    return app
