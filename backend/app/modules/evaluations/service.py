"""Evaluation forms and evaluations (plan 3.10 / 4.4)."""

import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import utcnow
from app.core.errors import AppError, conflict, forbidden, not_found, unprocessable
from app.core.pagination import PageParams, make_page, paginate
from app.core.permissions import can_manage_internship
from app.core.side_effects import audit, notify
from app.modules.evaluations import repository as repo
from app.modules.evaluations import schemas as s
from app.modules.evaluations.models import Evaluation, EvaluationCriterion, EvaluationForm, EvaluationScore
from app.modules.users.models import User

TWO_PLACES = Decimal("0.01")


# ---- scoring ------------------------------------------------------------------------------------------
def compute_weighted_score(criteria: dict[uuid.UUID, EvaluationCriterion], scores: dict[uuid.UUID, int]) -> Decimal:
    """100 * sum(score / max_score * weight) / sum(weight), rounded to 2 decimals (plan 6.7)."""
    total_weight = Decimal(0)
    acc = Decimal(0)
    for cid, crit in criteria.items():
        weight = Decimal(crit.weight)
        total_weight += weight
        acc += Decimal(scores[cid]) / Decimal(crit.max_score) * weight
    if total_weight == 0:
        return Decimal("0.00")
    return (Decimal(100) * acc / total_weight).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _validate_scores(form: EvaluationForm, scores: list[s.ScoreInput]) -> dict[uuid.UUID, int]:
    criteria = {c.id: c for c in form.criteria}
    given: dict[uuid.UUID, int] = {}
    details: list[dict[str, str]] = []
    for idx, item in enumerate(scores):
        crit = criteria.get(item.criterion_id)
        if crit is None:
            details.append({"field": f"scores.{idx}.criterion_id", "message": "Criterion does not belong to the form"})
            continue
        if item.criterion_id in given:
            details.append({"field": f"scores.{idx}.criterion_id", "message": "Duplicate criterion"})
            continue
        if item.score > crit.max_score:
            details.append(
                {"field": f"scores.{idx}.score", "message": f"Score must be between 0 and {crit.max_score}"}
            )
            continue
        given[item.criterion_id] = item.score
    missing = set(criteria) - set(given)
    if missing and not details:
        details.append({"field": "scores", "message": "A score is required for every criterion of the form"})
    if details:
        raise unprocessable("Invalid scores", details=details)
    return given


# ---- builders -----------------------------------------------------------------------------------------
def _form_out(form: EvaluationForm, in_use: bool) -> s.EvaluationForm:
    return s.EvaluationForm(
        id=form.id,
        name=form.name,
        description=form.description,
        is_default=form.is_default,
        criteria=[
            s.EvaluationCriterion(
                id=c.id,
                name=c.name,
                description=c.description,
                weight=float(c.weight),
                max_score=c.max_score,  # type: ignore[arg-type]  # DB CHECK limits it to 5 / 10
                position=c.position,
            )
            for c in sorted(form.criteria, key=lambda c: c.position)
        ],
        archived_at=form.archived_at,
        created_at=form.created_at,
        in_use=in_use,
    )


async def _evaluations_out(session: AsyncSession, evs: list[Evaluation]) -> list[s.Evaluation]:
    ctx = await repo.application_context(session, list({e.application_id for e in evs}))
    names = await repo.user_names(session, list({e.evaluator_id for e in evs}))
    out: list[s.Evaluation] = []
    for ev in evs:
        _app, internship, student = ctx[ev.application_id]
        scores = sorted(ev.scores, key=lambda sc: sc.criterion.position)
        out.append(
            s.Evaluation(
                id=ev.id,
                form_name=ev.form.name,
                evaluator_name=names.get(ev.evaluator_id, ""),
                weighted_score=ev.weighted_score,
                recommendation=ev.recommendation,  # type: ignore[arg-type]
                created_at=ev.created_at,
                shared_with_student=ev.shared_with_student,
                form_id=ev.form_id,
                application_id=ev.application_id,
                student=s.PersonRef(id=student.id, full_name=student.full_name),
                internship=s.InternshipRef(id=internship.id, title=internship.title),
                scores=[
                    s.EvaluationScoreOut(
                        criterion_id=sc.criterion_id,
                        criterion_name=sc.criterion.name,
                        score=sc.score,
                        max_score=sc.criterion.max_score,
                        weight=float(sc.criterion.weight),
                        comment=sc.comment,
                    )
                    for sc in scores
                ],
                overall_comments=ev.overall_comments,
                archived_at=ev.archived_at,
            )
        )
    return out


async def _one_out(session: AsyncSession, evaluation_id: uuid.UUID) -> s.Evaluation:
    ev = await repo.get_evaluation(session, evaluation_id)
    assert ev is not None
    return (await _evaluations_out(session, [ev]))[0]


# ---- forms --------------------------------------------------------------------------------------------
def _criterion_rows(form_id: uuid.UUID, items: list[s.CriterionInput]) -> list[EvaluationCriterion]:
    return [
        EvaluationCriterion(
            form_id=form_id,
            name=c.name,
            description=c.description,
            weight=Decimal(str(c.weight)).quantize(TWO_PLACES),
            max_score=c.max_score,
            position=i,
        )
        for i, c in enumerate(items, start=1)
    ]


async def list_forms(session: AsyncSession, include_archived: bool) -> list[s.EvaluationForm]:
    forms = await repo.list_forms(session, include_archived)
    used = await repo.forms_in_use(session, [f.id for f in forms])
    return [_form_out(f, f.id in used) for f in forms]


async def get_form(session: AsyncSession, form_id: uuid.UUID) -> s.EvaluationForm:
    form = await repo.get_form(session, form_id)
    if form is None:
        raise not_found("Evaluation form not found")
    return _form_out(form, await repo.form_in_use(session, form_id))


async def create_form(session: AsyncSession, actor: User, body: s.EvaluationFormCreateRequest) -> s.EvaluationForm:
    form = EvaluationForm(name=body.name, description=body.description, created_by=actor.id, is_default=False)
    session.add(form)
    await session.flush()
    session.add_all(_criterion_rows(form.id, body.criteria))
    await session.flush()
    audit(session, actor, "evaluation_form.create", "evaluation_form", form.id, after={"name": form.name})
    form = await repo.get_form(session, form.id)
    assert form is not None
    return _form_out(form, False)


def _ensure_form_owner(actor: User, form: EvaluationForm) -> None:
    if actor.role != "ADMIN" and form.created_by != actor.id:
        raise forbidden("Only the creator of the form or an admin can change it")


async def update_form(
    session: AsyncSession, actor: User, form_id: uuid.UUID, body: s.EvaluationFormUpdateRequest
) -> s.EvaluationForm:
    form = await repo.get_form(session, form_id, for_update=True)
    if form is None:
        raise not_found("Evaluation form not found")
    _ensure_form_owner(actor, form)
    if form.archived_at is not None:
        raise conflict("Archived forms cannot be edited")
    fields = body.model_fields_set
    before = {"name": form.name, "description": form.description}
    if "name" in fields and body.name is not None:
        form.name = body.name
    if "description" in fields:
        form.description = body.description
    if "criteria" in fields and body.criteria is not None:
        if await repo.form_in_use(session, form.id):
            raise AppError(409, "IN_USE", "This form is already used by evaluations; its criteria cannot be replaced")
        await repo.delete_criteria(session, form.id)
        session.add_all(_criterion_rows(form.id, body.criteria))
    await session.flush()
    audit(
        session,
        actor,
        "evaluation_form.update",
        "evaluation_form",
        form.id,
        before=before,
        after={"name": form.name, "description": form.description, "criteria_replaced": "criteria" in fields},
    )
    form = await repo.get_form(session, form.id)
    return _form_out(form, await repo.form_in_use(session, form.id))


async def archive_form(session: AsyncSession, actor: User, form_id: uuid.UUID) -> s.EvaluationForm:
    form = await repo.get_form(session, form_id, for_update=True)
    if form is None:
        raise not_found("Evaluation form not found")
    _ensure_form_owner(actor, form)
    if form.archived_at is None:
        form.archived_at = utcnow()
        await session.flush()
        audit(session, actor, "evaluation_form.archive", "evaluation_form", form.id)
    return _form_out(form, await repo.form_in_use(session, form.id))


# ---- evaluations --------------------------------------------------------------------------------------
async def create_evaluation(session: AsyncSession, actor: User, body: s.EvaluationCreateRequest) -> s.Evaluation:
    ctx = (await repo.application_context(session, [body.application_id])).get(body.application_id)
    if ctx is None:
        raise not_found("Application not found")
    application, internship, student = ctx
    if not await can_manage_internship(session, actor, internship):
        raise not_found("Application not found")
    form = await repo.get_form(session, body.form_id)
    if form is None:
        raise not_found("Evaluation form not found")
    if form.archived_at is not None:
        raise conflict("This evaluation form is archived")
    score_map = _validate_scores(form, body.scores)
    if await repo.duplicate_exists(session, application.id, actor.id, form.id):
        raise AppError(409, "DUPLICATE_EVALUATION", "You have already evaluated this application with this form")

    weighted = compute_weighted_score({c.id: c for c in form.criteria}, score_map)
    ev = Evaluation(
        form_id=form.id,
        application_id=application.id,
        evaluator_id=actor.id,
        overall_comments=body.overall_comments,
        recommendation=body.recommendation,
        weighted_score=weighted,
        shared_with_student=body.shared_with_student,
    )
    session.add(ev)
    await session.flush()
    comments = {x.criterion_id: x.comment for x in body.scores}
    session.add_all(
        EvaluationScore(evaluation_id=ev.id, criterion_id=cid, score=sc, comment=comments.get(cid))
        for cid, sc in score_map.items()
    )
    await session.flush()
    if ev.shared_with_student:
        _notify_shared(session, student.id, internship.title, ev.id, application.id)
    audit(
        session,
        actor,
        "evaluation.create",
        "evaluation",
        ev.id,
        after={
            "application_id": str(application.id),
            "form_id": str(form.id),
            "weighted_score": float(weighted),
            "recommendation": ev.recommendation,
        },
    )
    return await _one_out(session, ev.id)


def _notify_shared(
    session: AsyncSession, student_id: uuid.UUID, internship_title: str, evaluation_id: uuid.UUID, app_id: uuid.UUID
) -> None:
    notify(
        session,
        student_id,
        "EVALUATION_SHARED",
        "New evaluation available",
        f"An evaluation for {internship_title} was shared with you.",
        f"/student/applications/{app_id}",
        {"evaluation_id": str(evaluation_id), "application_id": str(app_id)},
    )


async def list_evaluations(
    session: AsyncSession,
    user: User,
    params: PageParams,
    *,
    application_id: uuid.UUID | None,
    internship_id: uuid.UUID | None,
    student_id: uuid.UUID | None,
    include_archived: bool = False,
) -> dict[str, Any]:
    from app.modules.applications.models import Application

    stmt = repo.base_select().where(await repo.scope_clause(session, user))
    if application_id is not None:
        stmt = stmt.where(Evaluation.application_id == application_id)
    if internship_id is not None:
        stmt = stmt.where(Application.internship_id == internship_id)
    if student_id is not None:
        stmt = stmt.where(Application.student_id == student_id)
    if user.role == "STUDENT" or not include_archived:
        stmt = stmt.where(Evaluation.archived_at.is_(None))
    stmt = stmt.order_by(Evaluation.created_at.desc(), Evaluation.id.asc())
    rows, total = await paginate(session, stmt, params)
    return make_page(await _evaluations_out(session, rows), total, params)


async def _visible(session: AsyncSession, user: User, evaluation_id: uuid.UUID) -> Evaluation:
    stmt = repo.base_select().where(Evaluation.id == evaluation_id, await repo.scope_clause(session, user))
    ev = (await session.execute(stmt)).scalar_one_or_none()
    if ev is None or (user.role == "STUDENT" and ev.archived_at is not None):
        raise not_found("Evaluation not found")
    return ev


async def get_evaluation(session: AsyncSession, user: User, evaluation_id: uuid.UUID) -> s.Evaluation:
    ev = await _visible(session, user, evaluation_id)
    return (await _evaluations_out(session, [ev]))[0]


async def _writable(session: AsyncSession, user: User, evaluation_id: uuid.UUID) -> Evaluation:
    await _visible(session, user, evaluation_id)
    ev = await repo.get_evaluation(session, evaluation_id, for_update=True)
    assert ev is not None
    if user.role != "ADMIN" and ev.evaluator_id != user.id:
        raise forbidden("Only the evaluator or an admin can change this evaluation")
    return ev


async def update_evaluation(
    session: AsyncSession, actor: User, evaluation_id: uuid.UUID, body: s.EvaluationUpdateRequest
) -> s.Evaluation:
    ev = await _writable(session, actor, evaluation_id)
    if ev.archived_at is not None:
        raise conflict("Archived evaluations cannot be edited")
    fields = body.model_fields_set
    before = {
        "weighted_score": float(ev.weighted_score),
        "recommendation": ev.recommendation,
        "shared_with_student": ev.shared_with_student,
    }
    was_shared = ev.shared_with_student
    if "scores" in fields and body.scores is not None:
        form = await repo.get_form(session, ev.form_id)
        assert form is not None
        score_map = _validate_scores(form, body.scores)
        ev.weighted_score = compute_weighted_score({c.id: c for c in form.criteria}, score_map)
        comments = {x.criterion_id: x.comment for x in body.scores}
        for row in ev.scores:  # same criterion set as the form: update in place
            row.score = score_map[row.criterion_id]
            row.comment = comments.get(row.criterion_id)
    if "overall_comments" in fields:
        ev.overall_comments = body.overall_comments
    if "recommendation" in fields and body.recommendation is not None:
        ev.recommendation = body.recommendation
    if "shared_with_student" in fields and body.shared_with_student is not None:
        ev.shared_with_student = body.shared_with_student
    await session.flush()
    if ev.shared_with_student and not was_shared:
        ctx = (await repo.application_context(session, [ev.application_id]))[ev.application_id]
        _notify_shared(session, ctx[2].id, ctx[1].title, ev.id, ev.application_id)
    audit(
        session,
        actor,
        "evaluation.update",
        "evaluation",
        ev.id,
        before=before,
        after={
            "weighted_score": float(ev.weighted_score),
            "recommendation": ev.recommendation,
            "shared_with_student": ev.shared_with_student,
        },
    )
    return await _one_out(session, ev.id)


async def archive_evaluation(session: AsyncSession, actor: User, evaluation_id: uuid.UUID) -> s.Evaluation:
    ev = await _writable(session, actor, evaluation_id)
    if ev.archived_at is None:
        ev.archived_at = utcnow()
        await session.flush()
        audit(session, actor, "evaluation.archive", "evaluation", ev.id)
    return await _one_out(session, ev.id)


async def delete_evaluation(session: AsyncSession, actor: User, evaluation_id: uuid.UUID) -> None:
    ev = await repo.get_evaluation(session, evaluation_id, for_update=True)
    if ev is None:
        raise not_found("Evaluation not found")
    audit(
        session,
        actor,
        "evaluation.delete",
        "evaluation",
        ev.id,
        before={"application_id": str(ev.application_id), "weighted_score": float(ev.weighted_score)},
    )
    await session.delete(ev)
    await session.flush()
