"""Application queries."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import utcnow
from app.core.pagination import PageParams
from app.core.permissions import member_company_id, owned_internships_clause
from app.modules.applications.models import Application, ApplicationStatusHistory
from app.modules.companies.models import Company
from app.modules.documents.models import Document
from app.modules.evaluations.models import Evaluation, EvaluationForm
from app.modules.feedback.models import CompanyFeedback, StudentFeedback
from app.modules.internships.models import Internship
from app.modules.interviews.models import Interview
from app.modules.students.models import Student
from app.modules.users.models import User


def _like(s: str) -> str:
    return "%" + s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


async def scope_clause(session: AsyncSession, user: User) -> Any:
    """Applications visible to ``user`` (S own; F/C own internships; A all)."""
    from sqlalchemy import true

    if user.role == "ADMIN":
        return true()
    if user.role == "STUDENT":
        return Application.student_id == user.id
    company_id = await member_company_id(session, user)
    owned = select(Internship.id).where(owned_internships_clause(user, company_id))
    return Application.internship_id.in_(owned)


def base_select() -> Any:
    return (
        select(Application)
        .join(Internship, Internship.id == Application.internship_id)
        .join(Company, Company.id == Internship.company_id)
        .join(Student, Student.user_id == Application.student_id)
        .join(User, User.id == Application.student_id)
    )


async def list_page(
    session: AsyncSession,
    user: User,
    params: PageParams,
    *,
    statuses: list[str],
    internship_id: uuid.UUID | None,
    student_id: uuid.UUID | None,
    q: str | None,
) -> tuple[list[Application], int]:
    conds: list[Any] = [await scope_clause(session, user)]
    if statuses:
        conds.append(Application.status.in_(statuses))
    if internship_id:
        conds.append(Application.internship_id == internship_id)
    if student_id:
        conds.append(Application.student_id == student_id)
    if q and q.strip():
        pat = _like(q.strip())
        conds.append(
            or_(
                User.full_name.ilike(pat, escape="\\"),
                User.email.ilike(pat, escape="\\"),
                Internship.title.ilike(pat, escape="\\"),
                Company.name.ilike(pat, escape="\\"),
            )
        )
    count_stmt = (
        select(func.count())
        .select_from(Application)
        .join(Internship, Internship.id == Application.internship_id)
        .join(Company, Company.id == Internship.company_id)
        .join(User, User.id == Application.student_id)
        .where(*conds)
    )
    total = (await session.execute(count_stmt)).scalar_one()
    rows = (
        (
            await session.execute(
                base_select()
                .where(*conds)
                .order_by(desc(Application.created_at), Application.id)
                .offset(params.offset)
                .limit(params.limit)
            )
        )
        .scalars()
        .all()
    )
    return list(rows), int(total)


async def summary_context(session: AsyncSession, apps: list[Application], *, student_view: bool) -> dict[str, Any]:
    """Batch-load everything ``ApplicationSummary`` needs for ``apps``."""
    if not apps:
        return {"internships": {}, "students": {}, "next_interview": {}, "eval_avg": {}, "logos": {}}
    internship_ids = {a.internship_id for a in apps}
    student_ids = {a.student_id for a in apps}
    app_ids = [a.id for a in apps]
    irows = (
        await session.execute(
            select(Internship, Company.name, Document.bucket, Document.object_key, Document.filename)
            .join(Company, Company.id == Internship.company_id)
            .outerjoin(Document, Document.id == Company.logo_document_id)
            .where(Internship.id.in_(internship_ids))
        )
    ).all()
    internships = {r[0].id: (r[0], r[1], (r[2], r[3], r[4]) if r[2] else None) for r in irows}
    srows = (
        await session.execute(
            select(User.id, User.full_name, User.email, Student.department, Student.gpa)
            .join(Student, Student.user_id == User.id)
            .where(User.id.in_(student_ids))
        )
    ).all()
    students = {r[0]: r for r in srows}
    nrows = (
        await session.execute(
            select(Interview.application_id, func.min(Interview.scheduled_at))
            .where(
                Interview.application_id.in_(app_ids),
                Interview.status.in_(("SCHEDULED", "RESCHEDULED")),
                Interview.scheduled_at > utcnow(),
            )
            .group_by(Interview.application_id)
        )
    ).all()
    ev_stmt = (
        select(Evaluation.application_id, func.avg(Evaluation.weighted_score))
        .where(Evaluation.application_id.in_(app_ids), Evaluation.archived_at.is_(None))
        .group_by(Evaluation.application_id)
    )
    if student_view:
        ev_stmt = ev_stmt.where(Evaluation.shared_with_student.is_(True))
    erows = (await session.execute(ev_stmt)).all()
    return {
        "internships": internships,
        "students": students,
        "next_interview": {r[0]: r[1] for r in nrows},
        "eval_avg": {r[0]: round(float(r[1]), 2) for r in erows if r[1] is not None},
    }


async def get(session: AsyncSession, application_id: uuid.UUID) -> Application | None:
    return (await session.execute(select(Application).where(Application.id == application_id))).scalar_one_or_none()


async def get_document(session: AsyncSession, document_id: uuid.UUID) -> Document | None:
    return (await session.execute(select(Document).where(Document.id == document_id))).scalar_one_or_none()


async def get_student(session: AsyncSession, user_id: uuid.UUID) -> Student | None:
    return (await session.execute(select(Student).where(Student.user_id == user_id))).scalar_one_or_none()


async def history_rows(session: AsyncSession, application_id: uuid.UUID) -> list[Any]:
    return list(
        (
            await session.execute(
                select(ApplicationStatusHistory, User.full_name)
                .outerjoin(User, User.id == ApplicationStatusHistory.changed_by)
                .where(ApplicationStatusHistory.application_id == application_id)
                .order_by(ApplicationStatusHistory.created_at, ApplicationStatusHistory.id)
            )
        ).all()
    )


async def interview_rows(session: AsyncSession, application_id: uuid.UUID) -> list[Any]:
    return list(
        (
            await session.execute(
                select(Interview, User.full_name)
                .join(User, User.id == Interview.scheduled_by)
                .where(Interview.application_id == application_id)
                .order_by(Interview.scheduled_at)
            )
        ).all()
    )


async def evaluation_rows(session: AsyncSession, application_id: uuid.UUID, *, shared_only: bool) -> list[Any]:
    stmt = (
        select(Evaluation, EvaluationForm.name, User.full_name)
        .join(EvaluationForm, EvaluationForm.id == Evaluation.form_id)
        .join(User, User.id == Evaluation.evaluator_id)
        .where(Evaluation.application_id == application_id, Evaluation.archived_at.is_(None))
        .order_by(Evaluation.created_at)
    )
    if shared_only:
        stmt = stmt.where(Evaluation.shared_with_student.is_(True))
    return list((await session.execute(stmt)).all())


async def feedback_ids(session: AsyncSession, application_id: uuid.UUID) -> tuple[uuid.UUID | None, list[uuid.UUID]]:
    sf = (
        await session.execute(select(StudentFeedback.id).where(StudentFeedback.application_id == application_id))
    ).scalar_one_or_none()
    cf = (
        await session.execute(
            select(CompanyFeedback.id)
            .where(CompanyFeedback.application_id == application_id)
            .order_by(CompanyFeedback.created_at)
        )
    ).scalars().all()
    return sf, list(cf)
