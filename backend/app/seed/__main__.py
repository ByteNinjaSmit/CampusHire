"""Demo data seed: ``python -m app.seed`` (idempotent; plan 7.4).

Writes rows directly (bypassing services) so it can create past-dated data, but every row satisfies the DB
constraints. Everything happens in ONE transaction. Skips when ``admin@campushire.dev`` already exists.
Set SEED_SKIP_UPLOAD=true to skip uploading the sample resume PDFs to MinIO (documents rows are still created).
"""

import asyncio
import logging
import os
import random
import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import hash_password
from app.core.storage import ensure_buckets, storage
from app.models import (
    AuditLog,
    Application,
    ApplicationStatusHistory,
    Company,
    CompanyFeedback,
    CompanyMember,
    Document,
    Evaluation,
    EvaluationCriterion,
    EvaluationScore,
    Faculty,
    FacultyFeedback,
    FeedbackActionItem,
    Internship,
    Interview,
    LoginEvent,
    Notification,
    Student,
    StudentFeedback,
    SystemFeedback,
    User,
)
from app.seed import data as d
from app.seed.resume_pdf import build_resume_pdf

log = logging.getLogger("app.seed")

DEFAULT_FORM_ID = uuid.UUID("00000000-0000-0000-0000-00000000e001")
NOW = datetime.now(UTC)
TODAY = NOW.date()
rnd = random.Random(42)


def ago(days: float, hours: float = 0) -> datetime:
    return NOW - timedelta(days=days, hours=hours)


def at_10(days_from_now: int) -> datetime:
    return (NOW + timedelta(days=days_from_now)).replace(hour=10, minute=0, second=0, microsecond=0)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def phone(i: int) -> str:
    return f"+9198765{i:05d}"


async def seed(session: AsyncSession) -> None:  # noqa: C901 - one linear script
    hashes = {role: hash_password(pw) for role, pw in d.PASSWORDS.items()}

    # ------------------------------------------------------------------ users
    users: dict[str, User] = {}

    def add_user(key: str, email: str, role: str, name: str, created_days_ago: float, verified: bool = True, ph: int = 0) -> User:
        created = ago(created_days_ago)
        u = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hashes[role],
            role=role,
            full_name=name,
            phone=phone(ph) if ph else None,
            is_active=True,
            email_verified_at=created + timedelta(hours=1) if verified else None,
            created_at=created,
            updated_at=created,
        )
        session.add(u)
        users[key] = u
        return u

    add_user("admin", d.ADMIN_EMAIL, "ADMIN", "Campus Admin", 90, ph=1)
    for i, f in enumerate(d.FACULTY, start=1):
        add_user(f.key, f.email, "FACULTY", f.full_name, 88 - i, ph=10 + i)
    for i, s in enumerate(d.STUDENTS, start=1):
        created_days = 80 if s.key == "student" else rnd.randint(2, 85)
        add_user(s.key, s.email, "STUDENT", s.full_name, created_days, verified=s.verified, ph=100 + i)
    add_user("company", d.COMPANY_USER_EMAIL, "COMPANY", d.COMPANY_USER_NAME, 87, ph=50)
    await session.flush()

    for f in d.FACULTY:
        session.add(Faculty(user_id=users[f.key].id, department=f.department, designation=f.designation, employee_id=f.employee_id))
    students: dict[str, Student] = {}
    for i, s in enumerate(d.STUDENTS, start=1):
        skills = rnd.sample(d.SKILL_POOL, rnd.randint(4, 6))
        st = Student(
            user_id=users[s.key].id,
            enrollment_no=f"ENR{2020 + (i % 3)}{i:04d}",
            department=s.department,
            gpa=Decimal(s.gpa),
            graduation_year=s.graduation_year,
            skills=skills,
            bio=f"{s.department} student passionate about building useful software and learning by doing.",
            linkedin_url=f"https://www.linkedin.com/in/{slug(s.full_name)}",
            github_url=f"https://github.com/{slug(s.full_name)}" if s.department in ("CSE", "IT", "ECE") else None,
            created_at=users[s.key].created_at,
            updated_at=users[s.key].created_at,
        )
        session.add(st)
        students[s.key] = st

    # ------------------------------------------------------------------ companies
    companies: dict[str, Company] = {}
    for c in d.COMPANIES:
        co = Company(
            id=uuid.uuid4(),
            name=c.name,
            registration_number=c.registration_number,
            industry=c.industry,
            location=c.location,
            website=c.website,
            description=c.description,
            contact_person_name=c.contact_person_name,
            contact_email=c.contact_email,
            contact_phone=phone(200 + len(companies)),
            status=c.status,
            created_by=users["admin"].id if c.status == "ACTIVE" else None,
            created_at=ago(88 if c.status == "ACTIVE" else 5),
            updated_at=ago(88 if c.status == "ACTIVE" else 5),
        )
        session.add(co)
        companies[c.key] = co
    await session.flush()
    session.add(CompanyMember(user_id=users["company"].id, company_id=companies["nimbus"].id, job_title=d.COMPANY_USER_JOB_TITLE))

    # ------------------------------------------------------------------ internships
    internships: dict[str, Internship] = {}
    for spec in d.INTERNSHIPS:
        if spec.status == "CLOSED":
            deadline = ago(130)
            start = TODAY - timedelta(days=120)
            end = TODAY - timedelta(days=30)
            weeks = round((end - start).days / 7)
            created = ago(140)
        else:
            deadline = NOW + timedelta(days=spec.deadline_days)
            start = deadline.date() + timedelta(days=spec.start_gap_days)
            end = start + timedelta(weeks=spec.weeks)
            weeks = spec.weeks
            created = ago(rnd.randint(15, 45))
        approved = spec.status in ("APPROVED", "CLOSED")
        it = Internship(
            id=uuid.uuid4(),
            company_id=companies[spec.company].id,
            posted_by=users[spec.owner].id,
            title=spec.title,
            description=spec.description,
            domain=spec.domain,
            location=spec.location,
            work_mode=spec.work_mode,
            stipend_monthly=Decimal(spec.stipend),
            currency="INR",
            duration_weeks=weeks,
            start_date=start,
            end_date=end,
            application_deadline=deadline,
            openings=spec.openings,
            skills=list(spec.skills),
            min_gpa=Decimal(spec.min_gpa) if spec.min_gpa else None,
            eligible_departments=list(spec.departments),
            status=spec.status,
            rejection_reason=spec.rejection_reason,
            approved_by=users["admin"].id if approved else None,
            approved_at=created + timedelta(days=1) if approved else None,
            created_at=created,
            updated_at=created,
        )
        session.add(it)
        internships[spec.key] = it
    await session.flush()

    # ------------------------------------------------------------------ resumes (ReportLab PDFs -> MinIO)
    skip_upload = os.environ.get("SEED_SKIP_UPLOAD", "").lower() in ("1", "true", "yes")
    if not skip_upload:
        ensure_buckets()
    pending_resume_age = {"student5": 10, "student9": 3, "student11": 1}
    resumes: dict[str, Document] = {}
    for s in d.STUDENTS:
        u, st = users[s.key], students[s.key]
        pdf = build_resume_pdf(
            s.full_name, s.email, u.phone or "", s.department, s.gpa, s.graduation_year, list(st.skills),
            st.bio or "Motivated student seeking a hands-on internship.",
        )
        doc_id = uuid.uuid4()
        filename = f"{slug(s.full_name)}-resume.pdf"
        key = f"{u.id}/{doc_id}/{filename}"
        if not skip_upload:
            await storage.put_object(settings.BUCKET_RESUMES, key, pdf, "application/pdf")
        is_pending = s.key in pending_resume_age or not s.verified
        created = ago(pending_resume_age[s.key]) if s.key in pending_resume_age else u.created_at + timedelta(days=1)
        doc = Document(
            id=doc_id,
            owner_id=u.id,
            kind="RESUME",
            bucket="resumes",
            object_key=key,
            filename=filename,
            content_type="application/pdf",
            size_bytes=len(pdf),
            status="UPLOADED",
            verification_status="PENDING" if is_pending else "VERIFIED",
            verified_by=None if is_pending else users["admin"].id,
            verified_at=None if is_pending else created + timedelta(days=1),
            created_at=created,
            updated_at=created,
        )
        session.add(doc)
        resumes[s.key] = doc
    await session.flush()
    for s in d.STUDENTS:
        students[s.key].default_resume_id = resumes[s.key].id
    await session.flush()

    # ------------------------------------------------------------------ applications + history
    paths = {
        "PENDING": ["PENDING"],
        "UNDER_REVIEW": ["PENDING", "UNDER_REVIEW"],
        "SHORTLISTED": ["PENDING", "UNDER_REVIEW", "SHORTLISTED"],
        "INTERVIEW": ["PENDING", "UNDER_REVIEW", "SHORTLISTED", "INTERVIEW"],
        "ACCEPTED": ["PENDING", "UNDER_REVIEW", "SHORTLISTED", "INTERVIEW", "ACCEPTED"],
        "REJECTED": ["PENDING", "UNDER_REVIEW", "REJECTED"],
        "WITHDRAWN": ["PENDING", "WITHDRAWN"],
    }
    owner_key = {spec.key: spec.owner for spec in d.INTERNSHIPS}
    apps: dict[tuple[str, str], Application] = {}
    for a in d.APPLICATIONS:
        it = internships[a.internship]
        st_user = users[a.student]
        closed = it.status == "CLOSED"
        if closed:
            age = rnd.randint(125, 130)
        else:
            age = rnd.randint(2, max(3, min(25, int((NOW - it.created_at).days) - 1)))
        created = ago(age, rnd.randint(0, 8))
        path = paths[a.status]
        # timestamps of each step (spread between created and the final change)
        final_at = ago(max(0.2, age - len(path) - rnd.randint(0, 3))) if not closed else ago(60 + rnd.randint(0, 10))
        if final_at < created:
            final_at = created + timedelta(hours=2)
        steps = [created + (final_at - created) * i / max(1, len(path) - 1) for i in range(len(path))]
        owner = users[owner_key[a.internship]]
        stipend = float(it.stipend_monthly)
        offer = (
            {
                "stipend_monthly": stipend,
                "start_date": it.start_date.isoformat(),
                "joining_location": it.location,
                "notes": "Please carry your college ID and original documents on the first day.",
            }
            if a.status == "ACCEPTED"
            else None
        )
        decision = {
            "REJECTED": "Thank you for applying. We are moving ahead with candidates whose profile is a closer match.",
            "ACCEPTED": "Congratulations! We are delighted to offer you this internship.",
        }.get(a.status)
        completed_at = it.end_date and datetime.combine(it.end_date, datetime.min.time(), tzinfo=UTC) if a.flags.get("completed") else None
        ap = Application(
            id=uuid.uuid4(),
            internship_id=it.id,
            student_id=st_user.id,
            resume_document_id=resumes[a.student].id,
            cover_letter=(
                f"Dear Hiring Team, I am {st_user.full_name}, a {students[a.student].department} student, and I am very "
                f"excited to apply for the {it.title} role. My coursework and projects have prepared me to contribute "
                "from day one, and I am eager to learn from your engineers. Thank you for your consideration."
            ),
            qualifications=(
                f"{students[a.student].department} student with GPA {students[a.student].gpa}. Skills: "
                f"{', '.join(students[a.student].skills[:4])}. Completed relevant coursework and two team projects."
            ),
            answers={
                "skills": list(students[a.student].skills[:4]),
                "coursework": "Data Structures, Databases, Operating Systems",
                "availability_from": it.start_date.isoformat(),
            },
            status=a.status,
            status_changed_at=steps[-1],
            decision_note=decision,
            offer_details=offer,
            withdrawn_reason="Accepted another offer." if a.status == "WITHDRAWN" else None,
            completed_at=completed_at,
            created_at=created,
            updated_at=steps[-1],
        )
        session.add(ap)
        apps[(a.student, a.internship)] = ap
        await session.flush()
        for i, to_status in enumerate(path):
            if i == 0:
                changed_by: uuid.UUID | None = st_user.id
            elif to_status == "WITHDRAWN":
                changed_by = st_user.id
            elif to_status == "INTERVIEW":
                changed_by = None  # system, via interview scheduling
            else:
                changed_by = owner.id
            session.add(
                ApplicationStatusHistory(
                    application_id=ap.id,
                    from_status=path[i - 1] if i else None,
                    to_status=to_status,
                    changed_by=changed_by,
                    note=decision if i == len(path) - 1 and i > 0 else None,
                    created_at=steps[i],
                )
            )
    await session.flush()

    # ------------------------------------------------------------------ interviews
    interviews: list[Interview] = []
    modes = ["ONLINE", "ONSITE", "PHONE", "ONLINE"]
    mode_i = 0

    def make_interview(a: d.ApplicationSeed, when: datetime, status: str, result: str = "PENDING", created: datetime | None = None) -> Interview:
        nonlocal mode_i
        ap = apps[(a.student, a.internship)]
        owner = users[owner_key[a.internship]]
        mode = modes[mode_i % len(modes)]
        mode_i += 1
        done = status == "COMPLETED"
        iv = Interview(
            id=uuid.uuid4(),
            application_id=ap.id,
            scheduled_by=owner.id,
            scheduled_at=when,
            duration_minutes=45,
            mode=mode,
            location="Main campus block, Room 204" if mode == "ONSITE" else None,
            meeting_link=f"https://meet.campushire.dev/{slug(a.student)}-{slug(a.internship)}" if mode == "ONLINE" else None,
            interviewer_name=owner.full_name,
            interviewer_email=owner.email,
            interviewer_user_id=owner.id,
            status=status,
            result=result,
            score=(4 if result == "PASS" else 2) if done else None,
            comments="Strong fundamentals and clear communication." if result == "PASS" else ("Needs more depth in core topics." if done else None),
            feedback_for_student=(
                "Great interview! Keep strengthening system design basics." if result == "PASS"
                else "Thank you for your time. Work on core fundamentals and reapply next cycle."
            ) if done else None,
            cancel_reason="Interviewer unavailable, will be rescheduled." if status == "CANCELLED" else None,
            created_at=created or ago(1),
            updated_at=created or ago(1),
        )
        session.add(iv)
        interviews.append(iv)
        return iv

    for a in d.APPLICATIONS:
        if "interview_in_days" in a.flags:
            make_interview(a, at_10(int(a.flags["interview_in_days"])), "SCHEDULED", created=ago(2))  # type: ignore[call-overload]  # flag is an int
        if "cancelled_interview_in_days" in a.flags:
            make_interview(a, at_10(int(a.flags["cancelled_interview_in_days"])), "CANCELLED", created=ago(3))  # type: ignore[call-overload]  # flag is an int
        if "past_interview" in a.flags:
            closed = internships[a.internship].status == "CLOSED"
            when = ago(135) if closed else ago(3)
            make_interview(a, when, "COMPLETED", str(a.flags["past_interview"]), created=when - timedelta(days=5))
    await session.flush()

    # ------------------------------------------------------------------ evaluations (default form)
    criteria = (
        await session.execute(
            select(EvaluationCriterion).where(EvaluationCriterion.form_id == DEFAULT_FORM_ID).order_by(EvaluationCriterion.position)
        )
    ).scalars().all()
    evaluations_n = 0
    for student_key, internship_key, evaluator_key, shared, recommendation, scores in d.EVALUATIONS:
        ap = apps[(student_key, internship_key)]
        total_w = sum(float(c.weight) for c in criteria)
        weighted = 100 * sum(sc / c.max_score * float(c.weight) for sc, c in zip(scores, criteria, strict=True)) / total_w
        ev = Evaluation(
            id=uuid.uuid4(),
            form_id=DEFAULT_FORM_ID,
            application_id=ap.id,
            evaluator_id=users[evaluator_key].id,
            overall_comments="Solid candidate with good potential." if recommendation != "MAYBE" else "Promising but needs more depth.",
            recommendation=recommendation,
            weighted_score=Decimal(str(round(weighted, 2))),
            shared_with_student=shared,
            created_at=ago(rnd.randint(1, 10)),
        )
        session.add(ev)
        await session.flush()
        for sc, c in zip(scores, criteria, strict=True):
            session.add(EvaluationScore(evaluation_id=ev.id, criterion_id=c.id, score=sc, comment=None))
        evaluations_n += 1

    # ------------------------------------------------------------------ feedback
    for student_key, days, culture, mentor, learning, env, overall, comment in d.STUDENT_FEEDBACK:
        ap = apps[(student_key, "C1")]
        session.add(
            StudentFeedback(
                application_id=ap.id,
                student_id=users[student_key].id,
                company_id=companies["nimbus"].id,
                internship_id=internships["C1"].id,
                company_culture=culture,
                mentorship=mentor,
                technical_learning=learning,
                work_environment=env,
                overall=overall,
                comments=comment,
                suggestions="More frequent one-on-one sessions would help.",
                is_anonymous=student_key == "student3",
                response_body="Thank you for the feedback, we are improving our onboarding." if student_key == "student" else None,
                responded_by=users["faculty"].id if student_key == "student" else None,
                responded_at=ago(5) if student_key == "student" else None,
                created_at=ago(days),
            )
        )
    for student_key, (ts, ss, pu, re_, tw, la, hire) in {
        "student": (5, 4, 5, 5, 4, 5, 5),
        "student3": (3, 4, 4, 4, 3, 4, 3),
        "student4": (5, 5, 5, 4, 5, 5, 5),
    }.items():
        session.add(
            CompanyFeedback(
                application_id=apps[(student_key, "C1")].id,
                author_id=users["faculty"].id,
                technical_skills=ts, soft_skills=ss, punctuality=pu, responsibility=re_, teamwork=tw, learning_ability=la,
                strengths="Quick learner, reliable and communicates well.",
                improvements="Could take more initiative in design discussions.",
                hire_likelihood=hire,
                created_at=ago(rnd.randint(5, 25)),
            )
        )
    session.add(
        FacultyFeedback(
            internship_id=internships["C1"].id,
            application_id=apps[("student", "C1")].id,
            faculty_id=users["faculty"].id,
            course_suitability=4, learning_outcomes=5, internship_quality=4,
            suggestions="Align the project scope with the final-year curriculum.",
            comments="Students gained strong practical exposure.",
            created_at=ago(15),
        )
    )
    session.add(
        FacultyFeedback(
            internship_id=internships["I5"].id,
            application_id=None,
            faculty_id=users["faculty2"].id,
            course_suitability=5, learning_outcomes=4, internship_quality=4,
            suggestions="Provide hardware kits to remote candidates.",
            comments="Well matched to the ECE embedded systems syllabus.",
            created_at=ago(8),
        )
    )
    system_rows: list[SystemFeedback] = []
    for user_key, ftype, title, desc, severity, status, priority in d.SYSTEM_FEEDBACK:
        row = SystemFeedback(
            id=uuid.uuid4(), user_id=users[user_key].id, type=ftype, title=title, description=desc, page_url="/internships",
            severity=severity, status=status, priority=priority,
            admin_notes="Reviewed by the product team." if status != "NEW" else None,
            created_at=ago(rnd.randint(3, 28)),
        )
        session.add(row)
        system_rows.append(row)
    await session.flush()
    for row, (title, item_status, due) in zip(
        [r for r in system_rows if r.status in ("TRIAGED", "PLANNED", "IN_PROGRESS")],
        [("Investigate upload stall", "IN_PROGRESS", 7), ("Design bulk shortlist UX", "OPEN", 14), ("Deduplicate notification emails", "OPEN", 3)],
        strict=True,
    ):
        session.add(FeedbackActionItem(system_feedback_id=row.id, title=title, assignee_id=users["admin"].id, status=item_status, due_date=TODAY + timedelta(days=due)))

    # ------------------------------------------------------------------ notifications
    templates = {
        "STUDENT": [
            ("APPLICATION_STATUS", "Your application was updated", "Your application status changed. Open it to see details.", "/student/applications"),
            ("INTERVIEW_SCHEDULED", "Interview scheduled", "An interview has been scheduled for your application.", "/student/interviews"),
            ("INTERNSHIP_APPROVED", "New internship matches your profile", "A new internship matching your skills is now open.", "/internships"),
            ("SYSTEM", "Verify your resume", "Your resume is awaiting verification by the placement cell.", "/documents"),
            ("APPLICATION_STATUS", "Application received", "We received your application.", "/student/applications"),
            ("SYSTEM", "Welcome to CampusHire", "Complete your profile to get better recommendations.", "/profile"),
        ],
        "FACULTY": [
            ("APPLICATION_STATUS", "New application received", "A student applied to one of your postings.", "/faculty/internships"),
            ("INTERNSHIP_APPROVED", "Internship approved", "Your internship posting was approved.", "/faculty/internships"),
            ("INTERVIEW_SCHEDULED", "Upcoming interview", "You have an interview scheduled soon.", "/faculty/interviews"),
            ("SYSTEM", "Evaluation pending", "Some shortlisted candidates still need evaluations.", "/faculty/evaluations"),
            ("SYSTEM", "Welcome to CampusHire", "Post internships and review candidates from your dashboard.", "/faculty"),
        ],
        "COMPANY": [
            ("APPLICATION_STATUS", "New application received", "A student applied to one of your postings.", "/company/internships"),
            ("INTERNSHIP_APPROVED", "Internship approved", "Your internship posting was approved.", "/company/internships"),
            ("INTERVIEW_SCHEDULED", "Upcoming interview", "You have an interview scheduled soon.", "/company/interviews"),
            ("SYSTEM", "Company verified", "Nimbus Labs is verified and can post internships.", "/company/profile"),
            ("SYSTEM", "Welcome to CampusHire", "Post internships and review candidates from your dashboard.", "/company"),
        ],
        "ADMIN": [
            ("SYSTEM", "Internship awaiting approval", "A faculty member submitted an internship for approval.", "/admin/internships"),
            ("SYSTEM", "Internship awaiting approval", "A company user submitted an internship for approval.", "/admin/internships"),
            ("COMPANY_REGISTERED", "Company awaiting approval", "Skyline Ventures registered and is waiting for approval.", "/admin/companies"),
            ("SYSTEM", "Compliance scan finished", "The daily compliance scan completed.", "/admin/compliance"),
            ("SYSTEM", "Weekly report ready", "Your weekly placement summary is ready.", "/admin/reports"),
            ("SYSTEM", "System healthy", "All services are operating normally.", "/admin/system"),
        ],
    }
    for key in ("admin", "faculty", "faculty2", "student", "student2", "student4", "company"):
        role = users[key].role
        for idx, (ntype, title, body, link) in enumerate(templates[role]):
            created = ago(idx * 1.5 + rnd.random())
            session.add(
                Notification(
                    user_id=users[key].id, type=ntype, title=title, body=body, link=link, data={},
                    read_at=created + timedelta(hours=3) if idx >= 3 else None, created_at=created,
                )
            )

    # ------------------------------------------------------------------ login events (~400, last 30 days)
    verified_users = [u for u in users.values() if u.email_verified_at]
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    ]
    last_login: dict[uuid.UUID, datetime] = {}
    for _ in range(400):
        u = rnd.choice(verified_users)
        when = ago(rnd.random() * 30)
        ok = rnd.random() < 0.9
        session.add(
            LoginEvent(
                user_id=u.id if ok or rnd.random() < 0.7 else None,
                email=u.email, success=ok, ip=f"10.0.{rnd.randint(0, 20)}.{rnd.randint(1, 254)}",
                user_agent=rnd.choice(agents), created_at=when,
            )
        )
        if ok and (u.id not in last_login or when > last_login[u.id]):
            last_login[u.id] = when
    for u in verified_users:
        if u.id in last_login:
            u.last_login_at = last_login[u.id]

    # ------------------------------------------------------------------ audit logs (~60)
    actions: list[tuple[str, str, uuid.UUID | None, str]] = []
    for it_key, it in internships.items():
        if it.status in ("APPROVED", "CLOSED"):
            actions.append(("internship.approve", "internship", it.id, "admin"))
        if it.status == "REJECTED":
            actions.append(("internship.reject", "internship", it.id, "admin"))
        actions.append(("internship.create", "internship", it.id, owner_key[it_key]))
    for ap in list(apps.values())[:25]:
        actions.append(("application.status_change", "application", ap.id, "admin"))
    for u in list(users.values())[:8]:
        actions.append(("user.create", "user", u.id, "admin"))
    for action, etype, eid, actor_key in actions[:62]:
        session.add(
            AuditLog(
                actor_id=users[actor_key].id, action=action, entity_type=etype, entity_id=eid,
                before=None, after={"seed": True}, ip="10.0.0.1", user_agent=agents[0], created_at=ago(rnd.random() * 45),
            )
        )
    await session.flush()

    # ------------------------------------------------------------------ compliance scan (owned by WP4)
    await _run_compliance_scan(session)

    log.info(
        "seeded: %d users, %d companies, %d internships, %d applications, %d interviews, %d evaluations",
        len(users), len(companies), len(internships), len(apps), len(interviews), evaluations_n,
    )


async def _run_compliance_scan(session: AsyncSession) -> None:
    try:
        from app.modules.admin import service as admin_service
    except ImportError as exc:
        log.warning("compliance scan skipped (app.modules.admin.service not available yet): %s", exc)
        return
    fn: Any = None
    for name in ("run_compliance_scan", "compliance_scan", "scan_compliance", "run_scan"):
        fn = getattr(admin_service, name, None)
        if fn:
            break
    if fn is None:
        log.warning("compliance scan skipped: no run_compliance_scan() in app.modules.admin.service")
        return
    try:
        async with session.begin_nested():
            await fn(session)
        log.info("compliance scan executed")
    except Exception:  # noqa: BLE001 - the scan is a nicety; never fail the seed because of it
        log.exception("compliance scan failed (seed continues)")


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            exists = (await session.execute(select(User.id).where(User.email == d.ADMIN_EMAIL))).first()
            if exists:
                log.info("seed skipped: %s already exists", d.ADMIN_EMAIL)
                return
            async with session.begin():
                await seed(session)
            log.info("seed committed")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
