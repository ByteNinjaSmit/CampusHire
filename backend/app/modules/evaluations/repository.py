"""Evaluation queries."""

import uuid
from typing import Any

from sqlalchemy import Select, delete, exists, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions import owned_internship_ids
from app.modules.applications.models import Application
from app.modules.evaluations.models import Evaluation, EvaluationCriterion, EvaluationForm, EvaluationScore
from app.modules.internships.models import Internship
from app.modules.users.models import User

# ---- forms --------------------------------------------------------------------------------------------


async def list_forms(session: AsyncSession, include_archived: bool) -> list[EvaluationForm]:
    stmt = select(EvaluationForm).options(selectinload(EvaluationForm.criteria))
    if not include_archived:
        stmt = stmt.where(EvaluationForm.archived_at.is_(None))
    stmt = stmt.order_by(EvaluationForm.is_default.desc(), EvaluationForm.created_at.desc())
    return list((await session.execute(stmt)).scalars().all())


async def get_form(session: AsyncSession, form_id: uuid.UUID, *, for_update: bool = False) -> EvaluationForm | None:
    stmt = (
        select(EvaluationForm)
        .where(EvaluationForm.id == form_id)
        .options(selectinload(EvaluationForm.criteria))
        .execution_options(populate_existing=True)
    )
    if for_update:
        stmt = stmt.with_for_update(of=EvaluationForm)
    return (await session.execute(stmt)).scalar_one_or_none()


async def forms_in_use(session: AsyncSession, form_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not form_ids:
        return set()
    rows = await session.execute(select(Evaluation.form_id).where(Evaluation.form_id.in_(form_ids)).distinct())
    return set(rows.scalars().all())


async def form_in_use(session: AsyncSession, form_id: uuid.UUID) -> bool:
    return bool(await session.scalar(select(exists().where(Evaluation.form_id == form_id))))


async def delete_criteria(session: AsyncSession, form_id: uuid.UUID) -> None:
    await session.execute(delete(EvaluationCriterion).where(EvaluationCriterion.form_id == form_id))


# ---- evaluations --------------------------------------------------------------------------------------


def base_select() -> Select[Any]:
    return (
        select(Evaluation)
        .join(Application, Application.id == Evaluation.application_id)
        .join(Internship, Internship.id == Application.internship_id)
        .options(selectinload(Evaluation.scores).selectinload(EvaluationScore.criterion), selectinload(Evaluation.form))
    )


async def scope_clause(session: AsyncSession, user: User) -> Any:
    if user.role == "ADMIN":
        return true()
    if user.role == "STUDENT":
        return (Application.student_id == user.id) & (Evaluation.shared_with_student.is_(True))
    owned = await owned_internship_ids(session, user)
    return Application.internship_id.in_(owned)


async def get_evaluation(
    session: AsyncSession, evaluation_id: uuid.UUID, *, for_update: bool = False
) -> Evaluation | None:
    stmt = base_select().where(Evaluation.id == evaluation_id).execution_options(populate_existing=True)
    if for_update:
        stmt = stmt.with_for_update(of=Evaluation)
    return (await session.execute(stmt)).scalar_one_or_none()


async def duplicate_exists(
    session: AsyncSession, application_id: uuid.UUID, evaluator_id: uuid.UUID, form_id: uuid.UUID
) -> bool:
    return bool(
        await session.scalar(
            select(
                exists().where(
                    Evaluation.application_id == application_id,
                    Evaluation.evaluator_id == evaluator_id,
                    Evaluation.form_id == form_id,
                )
            )
        )
    )


async def application_context(
    session: AsyncSession, application_ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[Application, Internship, User]]:
    """application_id -> (application, internship, student user)."""
    if not application_ids:
        return {}
    stmt = (
        select(Application, Internship, User)
        .join(Internship, Internship.id == Application.internship_id)
        .join(User, User.id == Application.student_id)
        .where(Application.id.in_(application_ids))
    )
    return {r[0].id: (r[0], r[1], r[2]) for r in (await session.execute(stmt)).all()}


async def user_names(session: AsyncSession, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not user_ids:
        return {}
    rows = await session.execute(select(User.id, User.full_name).where(User.id.in_(user_ids)))
    return {r[0]: r[1] for r in rows.all()}


async def average_scores(session: AsyncSession, application_id: uuid.UUID) -> float | None:
    """Average weighted_score of non-archived evaluations of an application (helper for other modules)."""
    val = await session.scalar(
        select(func.avg(Evaluation.weighted_score)).where(
            Evaluation.application_id == application_id, Evaluation.archived_at.is_(None)
        )
    )
    return float(val) if val is not None else None
