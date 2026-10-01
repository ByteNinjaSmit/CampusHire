import pytest
from sqlalchemy import func, select

from app.modules.admin.models import AuditLog
from app.modules.evaluations.models import EvaluationForm
from app.modules.evaluations.service import compute_weighted_score
from tests.factories import (
    auth_headers,
    make_admin,
    make_application,
    make_company_user,
    make_faculty,
    make_internship,
    make_student,
)

FORMS = "/api/v1/evaluation-forms"
EVALS = "/api/v1/evaluations"


def form_body(**over):
    data = {
        "name": "Backend Evaluation",
        "description": "For backend interns",
        "criteria": [
            {"name": "Coding", "weight": 3, "max_score": 10},
            {"name": "Communication", "weight": 1, "max_score": 5},
        ],
    }
    data.update(over)
    return data


async def create_form(client, user, **over):
    r = await client.post(FORMS, headers=auth_headers(user), json=form_body(**over))
    assert r.status_code == 201, r.text
    return r.json()


def scores_for(form, values, comment=None):
    return [
        {"criterion_id": c["id"], "score": v, **({"comment": comment} if comment else {})}
        for c, v in zip(form["criteria"], values, strict=True)
    ]


async def world(db, status="UNDER_REVIEW"):
    faculty = await make_faculty(db)
    student = await make_student(db)
    internship = await make_internship(db, faculty)
    application = await make_application(db, student, internship, status=status)
    return faculty, student, internship, application


def eval_body(form, application, values, **over):
    data = {
        "form_id": form["id"],
        "application_id": str(application.id),
        "scores": scores_for(form, values),
        "overall_comments": "Solid candidate",
        "recommendation": "YES",
        "shared_with_student": False,
    }
    data.update(over)
    return data


# ---- scoring formula --------------------------------------------------------------------------------------------


def test_weighted_score_formula():
    class C:
        def __init__(self, weight, max_score):
            self.weight, self.max_score = weight, max_score

    import uuid

    a, b = uuid.uuid4(), uuid.uuid4()
    criteria = {a: C(3, 10), b: C(1, 5)}
    # 100 * (8/10*3 + 5/5*1) / 4 = 85
    assert float(compute_weighted_score(criteria, {a: 8, b: 5})) == 85.0
    assert float(compute_weighted_score(criteria, {a: 0, b: 0})) == 0.0
    assert float(compute_weighted_score(criteria, {a: 10, b: 5})) == 100.0
    third = {a: C(1, 5), b: C(1, 5)}
    assert float(compute_weighted_score(third, {a: 1, b: 0})) == 20.0
    assert str(compute_weighted_score({a: C(1, 5)}, {a: 1})) == "20.00"
    # rounding to two decimals
    assert str(compute_weighted_score({a: C(3, 10)}, {a: 1})) == "10.00"
    assert str(compute_weighted_score({a: C(1, 10), b: C(2, 10)}, {a: 1, b: 1})) == "10.00"
    assert str(compute_weighted_score({a: C(1, 5), b: C(1, 10)}, {a: 1, b: 1})) == "15.00"
    assert str(compute_weighted_score({a: C(1, 5), b: C(2, 5)}, {a: 1, b: 2})) == "33.33"


# ---- forms ------------------------------------------------------------------------------------------------------


async def test_seeded_style_default_form_visible_in_list(client, db):
    admin = await make_admin(db)
    db.add(EvaluationForm(name="Standard Internship Evaluation", is_default=True))
    await db.flush()
    r = await client.get(FORMS, headers=auth_headers(admin))
    assert r.status_code == 200
    assert any(f["is_default"] for f in r.json())


async def test_form_crud(client, db):
    faculty = await make_faculty(db)
    admin = await make_admin(db)
    form = await create_form(client, faculty)
    assert form["in_use"] is False and form["is_default"] is False and form["archived_at"] is None
    assert [c["position"] for c in form["criteria"]] == [1, 2]
    assert [c["weight"] for c in form["criteria"]] == [3.0, 1.0]
    assert [c["max_score"] for c in form["criteria"]] == [10, 5]

    r = await client.get(f"{FORMS}/{form['id']}", headers=auth_headers(faculty))
    assert r.status_code == 200 and r.json()["name"] == "Backend Evaluation"

    r = await client.patch(f"{FORMS}/{form['id']}", headers=auth_headers(faculty), json={"name": "Renamed"})
    assert r.status_code == 200 and r.json()["name"] == "Renamed" and len(r.json()["criteria"]) == 2

    r = await client.patch(
        f"{FORMS}/{form['id']}",
        headers=auth_headers(faculty),
        json={"criteria": [{"name": "Only one", "weight": 2.5, "max_score": 5}]},
    )
    assert r.status_code == 200, r.text
    assert [c["name"] for c in r.json()["criteria"]] == ["Only one"]
    assert r.json()["criteria"][0]["weight"] == 2.5

    # admin may edit anyone's form, other faculty may not
    other = await make_faculty(db)
    assert (await client.patch(f"{FORMS}/{form['id']}", headers=auth_headers(other), json={"name": "Hijack"})).status_code == 403
    assert (await client.patch(f"{FORMS}/{form['id']}", headers=auth_headers(admin), json={"name": "By admin"})).status_code == 200

    r = await client.post(f"{FORMS}/{form['id']}/archive", headers=auth_headers(faculty))
    assert r.status_code == 200 and r.json()["archived_at"] is not None
    listed = await client.get(FORMS, headers=auth_headers(faculty))
    assert form["id"] not in {f["id"] for f in listed.json()}
    listed = await client.get(FORMS, headers=auth_headers(faculty), params={"include_archived": True})
    assert form["id"] in {f["id"] for f in listed.json()}
    audits = (await db.execute(select(func.count()).select_from(AuditLog).where(AuditLog.entity_type == "evaluation_form"))).scalar_one()
    assert audits >= 4


async def test_form_validation(client, db):
    faculty = await make_faculty(db)
    h = auth_headers(faculty)
    bad_cases = [
        form_body(criteria=[]),
        form_body(criteria=[{"name": "A", "weight": 0, "max_score": 5}]),
        form_body(criteria=[{"name": "A", "weight": 10.5, "max_score": 5}]),
        form_body(criteria=[{"name": "A", "weight": 1, "max_score": 7}]),
        form_body(criteria=[{"name": "A", "weight": 1, "max_score": 5}, {"name": "a", "weight": 1, "max_score": 5}]),
        form_body(name=""),
    ]
    for bad in bad_cases:
        r = await client.post(FORMS, headers=h, json=bad)
        assert r.status_code == 422, bad


async def test_form_permissions(client, db):
    student = await make_student(db)
    company_user = await make_company_user(db)
    faculty = await make_faculty(db)
    assert (await client.get(FORMS)).status_code == 401
    assert (await client.get(FORMS, headers=auth_headers(student))).status_code == 403
    assert (await client.post(FORMS, headers=auth_headers(student), json=form_body())).status_code == 403
    assert (await client.get(FORMS, headers=auth_headers(company_user))).status_code == 200
    assert (await client.post(FORMS, headers=auth_headers(company_user), json=form_body())).status_code == 403
    form = await create_form(client, faculty)
    assert (await client.get(f"{FORMS}/{form['id']}", headers=auth_headers(company_user))).status_code == 200


async def test_form_criteria_locked_when_in_use(client, db):
    faculty, _s, _i, application = await world(db)
    form = await create_form(client, faculty)
    r = await client.post(EVALS, headers=auth_headers(faculty), json=eval_body(form, application, [8, 5]))
    assert r.status_code == 201, r.text
    r = await client.patch(
        f"{FORMS}/{form['id']}",
        headers=auth_headers(faculty),
        json={"criteria": [{"name": "New", "weight": 1, "max_score": 5}]},
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "IN_USE"
    # metadata still editable, and in_use is reported
    r = await client.patch(f"{FORMS}/{form['id']}", headers=auth_headers(faculty), json={"description": "updated"})
    assert r.status_code == 200 and r.json()["in_use"] is True


# ---- evaluate ---------------------------------------------------------------------------------------------------


async def test_create_evaluation_computes_weighted_score(client, db):
    faculty, student, internship, application = await world(db)
    form = await create_form(client, faculty)
    r = await client.post(EVALS, headers=auth_headers(faculty), json=eval_body(form, application, [8, 5]))
    assert r.status_code == 201, r.text
    ev = r.json()
    assert ev["weighted_score"] == 85.0
    assert ev["recommendation"] == "YES" and ev["shared_with_student"] is False
    assert ev["evaluator_name"] == faculty.full_name and ev["form_name"] == "Backend Evaluation"
    assert ev["student"] == {"id": str(student.id), "full_name": student.full_name}
    assert ev["internship"]["id"] == str(internship.id)
    assert [s["criterion_name"] for s in ev["scores"]] == ["Coding", "Communication"]
    assert ev["scores"][0]["max_score"] == 10 and ev["scores"][0]["weight"] == 3.0
    assert ev["overall_comments"] == "Solid candidate"


async def test_score_validation(client, db):
    faculty, _s, _i, application = await world(db)
    form = await create_form(client, faculty)
    h = auth_headers(faculty)
    over_max = await client.post(EVALS, headers=h, json=eval_body(form, application, [8, 6]))
    assert over_max.status_code == 422 and over_max.json()["error"]["details"][0]["field"] == "scores.1.score"
    negative = await client.post(EVALS, headers=h, json=eval_body(form, application, [-1, 3]))
    assert negative.status_code == 422
    missing = await client.post(EVALS, headers=h, json=eval_body(form, application, [8, 5], scores=scores_for(form, [8, 5])[:1]))
    assert missing.status_code == 422
    unknown = scores_for(form, [8, 5])
    unknown[1]["criterion_id"] = "00000000-0000-0000-0000-000000000000"
    assert (await client.post(EVALS, headers=h, json=eval_body(form, application, [8, 5], scores=unknown))).status_code == 422
    dup = scores_for(form, [8, 5])
    dup[1]["criterion_id"] = dup[0]["criterion_id"]
    assert (await client.post(EVALS, headers=h, json=eval_body(form, application, [8, 5], scores=dup))).status_code == 422
    bad_rec = await client.post(EVALS, headers=h, json=eval_body(form, application, [8, 5], recommendation="PERHAPS"))
    assert bad_rec.status_code == 422


async def test_unique_per_application_evaluator_form(client, db):
    faculty, _s, _i, application = await world(db)
    form = await create_form(client, faculty)
    h = auth_headers(faculty)
    assert (await client.post(EVALS, headers=h, json=eval_body(form, application, [8, 5]))).status_code == 201
    r = await client.post(EVALS, headers=h, json=eval_body(form, application, [1, 1]))
    assert r.status_code == 409 and r.json()["error"]["code"] == "DUPLICATE_EVALUATION"
    # another form is fine
    form2 = await create_form(client, faculty, name="Second")
    assert (await client.post(EVALS, headers=h, json=eval_body(form2, application, [2, 2]))).status_code == 201
    # another evaluator is fine
    admin = await make_admin(db)
    assert (await client.post(EVALS, headers=auth_headers(admin), json=eval_body(form, application, [2, 2]))).status_code == 201


async def test_archived_form_cannot_be_used(client, db):
    faculty, _s, _i, application = await world(db)
    form = await create_form(client, faculty)
    await client.post(f"{FORMS}/{form['id']}/archive", headers=auth_headers(faculty))
    r = await client.post(EVALS, headers=auth_headers(faculty), json=eval_body(form, application, [8, 5]))
    assert r.status_code == 409


async def test_create_permissions(client, db):
    faculty, student, _i, application = await world(db)
    form = await create_form(client, faculty)
    other_faculty = await make_faculty(db)
    body = eval_body(form, application, [8, 5])
    assert (await client.post(EVALS, headers=auth_headers(student), json=body)).status_code == 403
    assert (await client.post(EVALS, json=body)).status_code == 401
    assert (await client.post(EVALS, headers=auth_headers(other_faculty), json=body)).status_code == 404
    cu = await make_company_user(db)
    internship = await make_internship(db, cu, company=cu.company)
    app2 = await make_application(db, student, internship, status="PENDING")
    assert (await client.post(EVALS, headers=auth_headers(cu), json=eval_body(form, app2, [3, 3]))).status_code == 201


# ---- read / update / archive / delete ---------------------------------------------------------------------------


async def test_list_and_get_scoping(client, db):
    faculty, student, internship, application = await world(db)
    other_faculty = await make_faculty(db)
    other_student = await make_student(db)
    form = await create_form(client, faculty)
    hidden = (
        await client.post(EVALS, headers=auth_headers(faculty), json=eval_body(form, application, [8, 5]))
    ).json()
    other_internship = await make_internship(db, other_faculty)
    other_app = await make_application(db, student, other_internship, status="PENDING")
    other_ev = (
        await client.post(EVALS, headers=auth_headers(other_faculty), json=eval_body(form, other_app, [4, 4]))
    ).json()

    def ids(resp):
        return {i["id"] for i in resp.json()["items"]}

    assert ids(await client.get(EVALS, headers=auth_headers(faculty))) == {hidden["id"]}
    assert ids(await client.get(EVALS, headers=auth_headers(other_faculty))) == {other_ev["id"]}
    admin = await make_admin(db)
    assert ids(await client.get(EVALS, headers=auth_headers(admin))) == {hidden["id"], other_ev["id"]}
    r = await client.get(EVALS, headers=auth_headers(admin), params={"internship_id": str(internship.id)})
    assert ids(r) == {hidden["id"]}
    r = await client.get(EVALS, headers=auth_headers(admin), params={"student_id": str(student.id)})
    assert ids(r) == {hidden["id"], other_ev["id"]}
    r = await client.get(EVALS, headers=auth_headers(admin), params={"application_id": str(other_app.id)})
    assert ids(r) == {other_ev["id"]}

    # students only see shared evaluations of their own applications
    assert ids(await client.get(EVALS, headers=auth_headers(student))) == set()
    assert (await client.get(f"{EVALS}/{hidden['id']}", headers=auth_headers(student))).status_code == 404
    await client.patch(f"{EVALS}/{hidden['id']}", headers=auth_headers(faculty), json={"shared_with_student": True})
    assert ids(await client.get(EVALS, headers=auth_headers(student))) == {hidden["id"]}
    assert (await client.get(f"{EVALS}/{hidden['id']}", headers=auth_headers(student))).status_code == 200
    assert ids(await client.get(EVALS, headers=auth_headers(other_student))) == set()
    assert (await client.get(f"{EVALS}/{hidden['id']}", headers=auth_headers(other_student))).status_code == 404
    assert (await client.get(f"{EVALS}/{hidden['id']}", headers=auth_headers(other_faculty))).status_code == 404


async def test_update_recomputes_score_and_notifies_when_shared(client, db, captured):
    faculty, student, _i, application = await world(db)
    form = await create_form(client, faculty)
    h = auth_headers(faculty)
    ev = (await client.post(EVALS, headers=h, json=eval_body(form, application, [8, 5]))).json()
    assert not [n for n in captured.notifications if n["type"] == "EVALUATION_SHARED"]
    r = await client.patch(
        f"{EVALS}/{ev['id']}",
        headers=h,
        json={"scores": scores_for(form, [10, 0], "tweaked"), "recommendation": "STRONG_YES", "shared_with_student": True, "overall_comments": "Updated"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["weighted_score"] == 75.0  # 100 * (3*1 + 0) / 4
    assert data["recommendation"] == "STRONG_YES" and data["overall_comments"] == "Updated"
    assert [s["score"] for s in data["scores"]] == [10, 0] and data["scores"][0]["comment"] == "tweaked"
    assert any(n["type"] == "EVALUATION_SHARED" and n["user_id"] == student.id for n in captured.notifications)
    # invalid score on update
    r = await client.patch(f"{EVALS}/{ev['id']}", headers=h, json={"scores": scores_for(form, [11, 0])})
    assert r.status_code == 422
    # only the evaluator or admin may update
    other = await make_faculty(db)
    assert (await client.patch(f"{EVALS}/{ev['id']}", headers=auth_headers(other), json={"recommendation": "NO"})).status_code == 404
    admin = await make_admin(db)
    r = await client.patch(f"{EVALS}/{ev['id']}", headers=auth_headers(admin), json={"recommendation": "NO"})
    assert r.status_code == 200 and r.json()["recommendation"] == "NO"
    assert (await client.patch(f"{EVALS}/{ev['id']}", headers=auth_headers(student), json={"recommendation": "NO"})).status_code == 403


async def test_owner_non_evaluator_cannot_update(client, db):
    faculty, _s, _i, application = await world(db)
    form = await create_form(client, faculty)
    admin = await make_admin(db)
    ev = (await client.post(EVALS, headers=auth_headers(admin), json=eval_body(form, application, [8, 5]))).json()
    r = await client.patch(f"{EVALS}/{ev['id']}", headers=auth_headers(faculty), json={"recommendation": "NO"})
    assert r.status_code == 403


async def test_archive_and_delete(client, db):
    faculty, student, _i, application = await world(db)
    form = await create_form(client, faculty)
    h = auth_headers(faculty)
    admin = await make_admin(db)
    ev = (await client.post(EVALS, headers=h, json=eval_body(form, application, [8, 5], shared_with_student=True))).json()

    r = await client.post(f"{EVALS}/{ev['id']}/archive", headers=h)
    assert r.status_code == 200 and r.json()["archived_at"] is not None
    assert (await client.get(EVALS, headers=h)).json()["total"] == 0
    assert (await client.get(EVALS, headers=h, params={"include_archived": True})).json()["total"] == 1
    assert (await client.get(f"{EVALS}/{ev['id']}", headers=auth_headers(student))).status_code == 404
    assert (await client.patch(f"{EVALS}/{ev['id']}", headers=h, json={"recommendation": "NO"})).status_code == 409

    assert (await client.delete(f"{EVALS}/{ev['id']}", headers=h)).status_code == 403
    assert (await client.delete(f"{EVALS}/{ev['id']}", headers=auth_headers(student))).status_code == 403
    r = await client.delete(f"{EVALS}/{ev['id']}", headers=auth_headers(admin))
    assert r.status_code == 204
    assert (await client.get(f"{EVALS}/{ev['id']}", headers=auth_headers(admin))).status_code == 404
    actions = (await db.execute(select(AuditLog.action).where(AuditLog.entity_type == "evaluation"))).scalars().all()
    assert {"evaluation.create", "evaluation.archive", "evaluation.delete"} <= set(actions)
    # the form is no longer in use after the hard delete
    assert (await client.get(f"{FORMS}/{form['id']}", headers=h)).json()["in_use"] is False


@pytest.mark.parametrize("path", ["", "/{id}"])
async def test_requires_auth(client, path):
    assert (await client.get(EVALS + path.format(id="00000000-0000-0000-0000-000000000000"))).status_code == 401
