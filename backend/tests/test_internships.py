from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.admin.models import AuditLog
from app.modules.internships.models import Internship
from tests.factories import (
    auth_headers,
    make_admin,
    make_application,
    make_company,
    make_company_user,
    make_faculty,
    make_internship,
    make_student,
)

URL = "/api/v1/internships"


def body(company, **over):
    now = datetime.now(UTC)
    start = (now + timedelta(days=30)).date()
    data = {
        "company_id": str(company.id),
        "title": "Backend Engineering Intern",
        "description": "Build and ship backend services with a friendly and experienced team.",
        "domain": "Software Engineering",
        "location": "Bengaluru",
        "work_mode": "HYBRID",
        "stipend_monthly": 25000,
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(weeks=12)).isoformat(),
        "application_deadline": (now + timedelta(days=10)).isoformat().replace("+00:00", "Z"),
        "skills": ["Python", "SQL"],
    }
    data.update(over)
    return data


def ids(resp):
    return [i["id"] for i in resp.json()["items"]]


# ---- creation & validation ---------------------------------------------------------------------------------------


async def test_faculty_create_draft_submit_approve_flow(client, db, captured):
    fac = await make_faculty(db)
    admin = await make_admin(db)
    company = await make_company(db)
    r = await client.post(URL, headers=auth_headers(fac), json=body(company))
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "DRAFT"
    assert data["duration_weeks"] == 12
    assert isinstance(data["stipend_monthly"], float)
    assert data["posted_by"]["id"] == str(fac.id)
    assert data["can_edit"] is True
    iid = data["id"]

    r = await client.post(f"{URL}/{iid}/submit", headers=auth_headers(fac))
    assert r.status_code == 200 and r.json()["status"] == "PENDING_APPROVAL"
    assert any(n["user_id"] == admin.id and n["type"] == "INTERNSHIP_SUBMITTED" for n in captured.notifications)

    # faculty cannot approve
    assert (await client.post(f"{URL}/{iid}/approve", headers=auth_headers(fac))).status_code == 403
    r = await client.post(f"{URL}/{iid}/approve", headers=auth_headers(admin))
    assert r.status_code == 200 and r.json()["status"] == "APPROVED"
    assert captured.emails_to(fac.email, "internship_approved")
    assert any(n["user_id"] == fac.id and n["type"] == "INTERNSHIP_APPROVED" for n in captured.notifications)
    actions = (await db.execute(select(AuditLog.action).where(AuditLog.entity_type == "internship"))).scalars().all()
    assert {"internship.create", "internship.submit", "internship.approve"} <= set(actions)

    # approving twice -> invalid transition
    r = await client.post(f"{URL}/{iid}/approve", headers=auth_headers(admin))
    assert r.status_code == 409 and r.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


async def test_reject_requires_reason_and_can_resubmit(client, db, captured):
    fac = await make_faculty(db)
    admin = await make_admin(db)
    company = await make_company(db)
    iid = (await client.post(URL, headers=auth_headers(fac), json=body(company, submit=True))).json()["id"]
    assert (await client.post(f"{URL}/{iid}/reject", headers=auth_headers(admin), json={})).status_code == 422
    r = await client.post(f"{URL}/{iid}/reject", headers=auth_headers(admin), json={"reason": "Description too vague"})
    assert r.status_code == 200
    assert r.json()["status"] == "REJECTED" and r.json()["rejection_reason"] == "Description too vague"
    mails = captured.emails_to(fac.email, "internship_rejected")
    assert mails and mails[0]["context"]["reason"] == "Description too vague"
    r = await client.post(f"{URL}/{iid}/submit", headers=auth_headers(fac))
    assert r.status_code == 200 and r.json()["status"] == "PENDING_APPROVAL"


async def test_admin_creates_approved_directly(client, db):
    admin = await make_admin(db)
    company = await make_company(db)
    r = await client.post(URL, headers=auth_headers(admin), json=body(company))
    assert r.status_code == 201 and r.json()["status"] == "APPROVED"
    r = await client.post(URL, headers=auth_headers(admin), json=body(company, submit=False))
    assert r.json()["status"] == "DRAFT"


async def test_student_cannot_create(client, db):
    student = await make_student(db)
    company = await make_company(db)
    assert (await client.post(URL, headers=auth_headers(student), json=body(company))).status_code == 403
    assert (await client.post(URL, json=body(company))).status_code == 401


async def test_company_user_posting_rules(client, db):
    cu = await make_company_user(db)
    other = await make_company(db)
    r = await client.post(URL, headers=auth_headers(cu), json=body(cu.company, submit=True))
    assert r.status_code == 201 and r.json()["status"] == "PENDING_APPROVAL"
    assert (await client.post(URL, headers=auth_headers(cu), json=body(other))).status_code == 403
    pending = await make_company(db, status="PENDING")
    pu = await make_company_user(db, pending)
    assert (await client.post(URL, headers=auth_headers(pu), json=body(pending))).status_code == 403
    fac = await make_faculty(db)
    r = await client.post(URL, headers=auth_headers(fac), json=body(pending))
    assert r.status_code == 422


async def test_start_after_end_422(client, db):
    fac = await make_faculty(db)
    company = await make_company(db)
    start = (datetime.now(UTC) + timedelta(days=40)).date()
    r = await client.post(
        URL, headers=auth_headers(fac), json=body(company, start_date=start.isoformat(), end_date=(start - timedelta(days=5)).isoformat())
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert any(d["field"] == "end_date" for d in r.json()["error"]["details"])


async def test_start_in_past_422(client, db):
    fac = await make_faculty(db)
    company = await make_company(db)
    start = (datetime.now(UTC) - timedelta(days=5)).date()
    r = await client.post(
        URL,
        headers=auth_headers(fac),
        json=body(
            company,
            start_date=start.isoformat(),
            end_date=(start + timedelta(weeks=8)).isoformat(),
            application_deadline=(datetime.now(UTC) - timedelta(days=9)).isoformat(),
        ),
    )
    assert r.status_code == 422
    fields = {d["field"] for d in r.json()["error"]["details"]}
    assert "start_date" in fields and "application_deadline" in fields


async def test_deadline_after_start_422(client, db):
    fac = await make_faculty(db)
    company = await make_company(db)
    start = datetime.now(UTC) + timedelta(days=20)
    r = await client.post(
        URL,
        headers=auth_headers(fac),
        json=body(
            company,
            start_date=start.date().isoformat(),
            end_date=(start + timedelta(weeks=8)).date().isoformat(),
            application_deadline=(start + timedelta(days=1)).isoformat(),
        ),
    )
    assert r.status_code == 422
    assert any(d["field"] == "application_deadline" for d in r.json()["error"]["details"])


async def test_deadline_in_past_422(client, db):
    fac = await make_faculty(db)
    company = await make_company(db)
    r = await client.post(
        URL, headers=auth_headers(fac), json=body(company, application_deadline=(datetime.now(UTC) - timedelta(hours=1)).isoformat())
    )
    assert r.status_code == 422
    assert any(d["field"] == "application_deadline" for d in r.json()["error"]["details"])


def _dated(company, days):
    start = (datetime.now(UTC) + timedelta(days=30)).date()
    return body(company, start_date=start.isoformat(), end_date=(start + timedelta(days=days)).isoformat(), duration_weeks=None)


@pytest.mark.parametrize("days", [27, 184])
async def test_duration_out_of_range_422(client, db, days):
    fac = await make_faculty(db)
    company = await make_company(db)
    payload = _dated(company, days)
    payload.pop("duration_weeks")
    r = await client.post(URL, headers=auth_headers(fac), json=payload)
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("days,weeks", [(28, 4), (183, 26)])
async def test_duration_bounds_ok(client, db, days, weeks):
    fac = await make_faculty(db)
    company = await make_company(db)
    payload = _dated(company, days)
    payload.pop("duration_weeks")
    r = await client.post(URL, headers=auth_headers(fac), json=payload)
    assert r.status_code == 201, r.text
    assert r.json()["duration_weeks"] == weeks


async def test_duration_weeks_mismatch_422(client, db):
    fac = await make_faculty(db)
    company = await make_company(db)
    r = await client.post(URL, headers=auth_headers(fac), json=body(company, duration_weeks=20))  # dates span 12 weeks
    assert r.status_code == 422
    assert any(d["field"] == "duration_weeks" for d in r.json()["error"]["details"])
    assert (await client.post(URL, headers=auth_headers(fac), json=body(company, duration_weeks=13))).status_code == 201  # +-1


async def test_field_validation_422(client, db):
    fac = await make_faculty(db)
    company = await make_company(db)
    h = auth_headers(fac)
    assert (await client.post(URL, headers=h, json=body(company, domain="Underwater Basket Weaving"))).status_code == 422
    assert (await client.post(URL, headers=h, json=body(company, stipend_monthly=-1))).status_code == 422
    assert (await client.post(URL, headers=h, json=body(company, title="ab"))).status_code == 422
    assert (await client.post(URL, headers=h, json=body(company, description="too short"))).status_code == 422
    assert (await client.post(URL, headers=h, json=body(company, min_gpa=4.5))).status_code == 422
    assert (await client.post(URL, headers=h, json=body(company, work_mode="MOON"))).status_code == 422


async def test_db_check_dates(db):
    fac = await make_faculty(db)
    with pytest.raises(IntegrityError):
        await make_internship(db, fac, start_date=date(2030, 6, 1), end_date=date(2030, 5, 1))


# ---- update / lifecycle -------------------------------------------------------------------------------------------


async def test_update_core_fields_on_approved_returns_to_pending(client, db):
    fac = await make_faculty(db)
    admin = await make_admin(db)
    it = await make_internship(db, fac)
    r = await client.patch(f"{URL}/{it.id}", headers=auth_headers(fac), json={"location": "Mumbai", "openings": 5})
    assert r.status_code == 200 and r.json()["status"] == "APPROVED" and r.json()["location"] == "Mumbai"
    r = await client.patch(f"{URL}/{it.id}", headers=auth_headers(fac), json={"title": "Renamed Intern Role"})
    assert r.json()["status"] == "PENDING_APPROVAL" and r.json()["title"] == "Renamed Intern Role"
    # admin edits do not reset the status
    it2 = await make_internship(db, fac)
    r = await client.patch(f"{URL}/{it2.id}", headers=auth_headers(admin), json={"title": "Admin Edited Title"})
    assert r.json()["status"] == "APPROVED"


async def test_update_dates_revalidated(client, db):
    fac = await make_faculty(db)
    it = await make_internship(db, fac, status="DRAFT")
    r = await client.patch(
        f"{URL}/{it.id}", headers=auth_headers(fac), json={"end_date": (it.start_date - timedelta(days=1)).isoformat()}
    )
    assert r.status_code == 422
    new_end = it.end_date + timedelta(weeks=2)
    r = await client.patch(f"{URL}/{it.id}", headers=auth_headers(fac), json={"end_date": new_end.isoformat()})
    assert r.status_code == 200 and r.json()["duration_weeks"] == 14


async def test_owner_scoping_404_for_other_faculty(client, db):
    a = await make_faculty(db)
    b = await make_faculty(db)
    it = await make_internship(db, a, status="DRAFT")
    hb = auth_headers(b)
    assert (await client.patch(f"{URL}/{it.id}", headers=hb, json={"location": "X-City"})).status_code == 404
    assert (await client.post(f"{URL}/{it.id}/submit", headers=hb)).status_code == 404
    assert (await client.get(f"{URL}/{it.id}", headers=hb)).status_code == 404  # DRAFT is private
    assert (await client.get(f"{URL}/{it.id}/applications", headers=hb)).status_code == 404
    assert (await client.patch(f"{URL}/{it.id}", headers=auth_headers(a), json={"location": "X-City"})).status_code == 200


async def test_company_members_share_ownership(client, db):
    cu1 = await make_company_user(db)
    cu2 = await make_company_user(db, cu1.company)
    other = await make_company_user(db)
    it = await make_internship(db, cu1, company=cu1.company, status="DRAFT")
    assert (await client.patch(f"{URL}/{it.id}", headers=auth_headers(cu2), json={"location": "Pune"})).status_code == 200
    assert (await client.patch(f"{URL}/{it.id}", headers=auth_headers(other), json={"location": "Pune"})).status_code == 404


async def test_close_archive_restore_delete(client, db):
    fac = await make_faculty(db)
    admin = await make_admin(db)
    student = await make_student(db)
    it = await make_internship(db, fac)
    h = auth_headers(fac)
    r = await client.post(f"{URL}/{it.id}/close", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "CLOSED"
    assert (await client.post(f"{URL}/{it.id}/close", headers=h)).status_code == 409
    assert (await client.patch(f"{URL}/{it.id}", headers=h, json={"location": "Delhi"})).status_code == 409
    r = await client.post(f"{URL}/{it.id}/archive", headers=h)
    assert r.status_code == 200 and r.json()["archived_at"] is not None
    assert (await client.post(f"{URL}/{it.id}/restore", headers=h)).status_code == 403  # admin only
    r = await client.post(f"{URL}/{it.id}/restore", headers=auth_headers(admin))
    assert r.json()["archived_at"] is None
    # delete: only admin, blocked when applications exist
    assert (await client.delete(f"{URL}/{it.id}", headers=h)).status_code == 403
    await make_application(db, student, it)
    r = await client.delete(f"{URL}/{it.id}", headers=auth_headers(admin))
    assert r.status_code == 409 and r.json()["error"]["code"] == "IN_USE"
    empty = await make_internship(db, fac)
    assert (await client.delete(f"{URL}/{empty.id}", headers=auth_headers(admin))).status_code == 204
    assert (await client.get(f"{URL}/{empty.id}", headers=auth_headers(admin))).status_code == 404


async def test_bulk_actions(client, db):
    fac = await make_faculty(db)
    admin = await make_admin(db)
    p1 = await make_internship(db, fac, status="PENDING_APPROVAL")
    p2 = await make_internship(db, fac, status="PENDING_APPROVAL")
    draft = await make_internship(db, fac, status="DRAFT")
    r = await client.post(
        f"{URL}/bulk", headers=auth_headers(admin), json={"ids": [str(p1.id), str(p2.id), str(draft.id)], "action": "approve"}
    )
    assert r.status_code == 200
    out = r.json()
    assert set(out["updated"]) == {str(p1.id), str(p2.id)}
    assert out["failed"][0]["id"] == str(draft.id) and out["failed"][0]["code"] == "INVALID_STATUS_TRANSITION"
    assert (
        await client.post(f"{URL}/bulk", headers=auth_headers(admin), json={"ids": [str(p1.id)], "action": "reject"})
    ).status_code == 422
    assert (
        await client.post(f"{URL}/bulk", headers=auth_headers(fac), json={"ids": [str(p1.id)], "action": "archive"})
    ).status_code == 403


# ---- list / search / filters --------------------------------------------------------------------------------------


async def test_student_list_only_open_approved(client, db):
    fac = await make_faculty(db)
    student = await make_student(db)
    company = await make_company(db)
    ok = await make_internship(db, fac, company=company)
    await make_internship(db, fac, company=company, status="DRAFT")
    await make_internship(db, fac, company=company, status="PENDING_APPROVAL")
    await make_internship(db, fac, company=company, status="CLOSED")
    await make_internship(db, fac, company=company, deadline_in_days=-2)
    archived = await make_internship(db, fac, company=company)
    archived.archived_at = datetime.now(UTC)
    await db.flush()
    r = await client.get(URL, headers=auth_headers(student), params={"status": "DRAFT", "include_archived": True})
    assert r.status_code == 200
    assert ids(r) == [str(ok.id)]
    assert r.json()["total"] == 1 and r.json()["pages"] == 1
    item = r.json()["items"][0]
    assert item["company"]["name"] == company.name and item["is_saved"] is False and isinstance(item["stipend_monthly"], float)


async def test_staff_mine_and_admin_all(client, db):
    a = await make_faculty(db)
    b = await make_faculty(db)
    admin = await make_admin(db)
    own_draft = await make_internship(db, a, status="DRAFT")
    own_open = await make_internship(db, a)
    other_open = await make_internship(db, b)
    other_draft = await make_internship(db, b, status="DRAFT")
    r = await client.get(URL, headers=auth_headers(a), params={"mine": True})
    assert set(ids(r)) == {str(own_draft.id), str(own_open.id)}
    r = await client.get(URL, headers=auth_headers(a))
    assert set(ids(r)) == {str(own_open.id), str(other_open.id)}
    r = await client.get(URL, headers=auth_headers(admin), params={"page_size": 100})
    assert {str(own_draft.id), str(other_draft.id), str(own_open.id), str(other_open.id)} <= set(ids(r))
    assert r.json()["items"][0]["application_count"] == 0
    r = await client.get(URL, headers=auth_headers(admin), params={"status": "DRAFT", "page_size": 100})
    assert {i["status"] for i in r.json()["items"]} == {"DRAFT"}


async def test_filters_sort_and_pagination(client, db):
    fac = await make_faculty(db)
    student = await make_student(db)
    h = auth_headers(student)
    c1, c2 = await make_company(db, name="Alpha Labs"), await make_company(db, name="Beta Works")
    i1 = await make_internship(db, fac, company=c1, domain="Data Science", location="Pune", work_mode="REMOTE", stipend_monthly=10000, weeks=8, skills=["Pandas", "SQL"], deadline_in_days=30)
    i2 = await make_internship(db, fac, company=c2, domain="Cybersecurity", location="Mumbai", work_mode="ONSITE", stipend_monthly=30000, weeks=16, skills=["Networking"], deadline_in_days=10)
    i3 = await make_internship(db, fac, company=c2, domain="Data Science", location="Pune", work_mode="HYBRID", stipend_monthly=20000, weeks=12, skills=["Python"], deadline_in_days=20)

    async def q(**params):
        return ids(await client.get(URL, headers=h, params={"sort": "newest", **params}))

    assert set(await q(domain="Data Science")) == {str(i1.id), str(i3.id)}
    assert set(await q(domain=["Data Science", "Cybersecurity"])) == {str(i1.id), str(i2.id), str(i3.id)}
    assert set(await q(company_id=str(c2.id))) == {str(i2.id), str(i3.id)}
    assert set(await q(location="pun")) == {str(i1.id), str(i3.id)}
    assert set(await q(work_mode="REMOTE")) == {str(i1.id)}
    assert set(await q(stipend_min=15000, stipend_max=25000)) == {str(i3.id)}
    assert set(await q(duration_min=10)) == {str(i2.id), str(i3.id)}
    assert set(await q(duration_max=8)) == {str(i1.id)}
    assert set(await q(skills="sql")) == {str(i1.id)}
    assert await q(sort="stipend_desc") == [str(i2.id), str(i3.id), str(i1.id)]
    assert await q(sort="deadline_asc") == [str(i2.id), str(i3.id), str(i1.id)]
    soon = (datetime.now(UTC) + timedelta(days=15)).isoformat()
    assert set(await q(deadline_before=soon)) == {str(i2.id)}
    r = await client.get(URL, headers=h, params={"sort": "stipend_desc", "page": 2, "page_size": 2})
    body_ = r.json()
    assert body_["total"] == 3 and body_["pages"] == 2 and ids(r) == [str(i1.id)]
    assert (await client.get(URL, headers=h, params={"page_size": 101})).status_code == 422


async def test_search_fts_and_trigram(client, db):
    fac = await make_faculty(db)
    student = await make_student(db)
    h = auth_headers(student)
    ml = await make_internship(db, fac, title="Machine Learning Engineer Intern", domain="AI/ML", description="Train and evaluate neural networks on large datasets.")
    fe = await make_internship(db, fac, title="Frontend React Intern", domain="Software Engineering", description="Build accessible user interfaces with modern tooling.")
    acme = await make_company(db, name="Zephyrix Technologies")
    zz = await make_internship(db, fac, company=acme, title="Operations Associate", domain="Operations", description="Coordinate day to day operations and reporting for the team.")

    r = await client.get(URL, headers=h, params={"q": "machine learning"})
    assert ids(r)[0] == str(ml.id) and str(fe.id) not in ids(r)
    r = await client.get(URL, headers=h, params={"q": "neural networks"})  # description (weight D)
    assert ids(r) == [str(ml.id)]
    r = await client.get(URL, headers=h, params={"q": "Fronted React"})  # typo -> trigram similarity
    assert str(fe.id) in ids(r)
    r = await client.get(URL, headers=h, params={"q": "Zephyrix"})  # company name trigram
    assert ids(r) == [str(zz.id)]
    r = await client.get(URL, headers=h, params={"q": "kubernetes-quantum-zebra"})
    assert r.status_code == 200 and ids(r) == []


async def test_facets(client, db):
    fac = await make_faculty(db)
    student = await make_student(db)
    c = await make_company(db, name="Facet Co")
    await make_internship(db, fac, company=c, domain="Finance", location="Delhi", work_mode="ONSITE", stipend_monthly=5000)
    await make_internship(db, fac, company=c, domain="Finance", location="Delhi", work_mode="REMOTE", stipend_monthly=9000)
    await make_internship(db, fac, company=c, domain="Marketing", location="Goa", work_mode="REMOTE", stipend_monthly=7000)
    await make_internship(db, fac, company=c, status="DRAFT", domain="Research", stipend_monthly=99999)
    r = await client.get(f"{URL}/facets", headers=auth_headers(student))
    assert r.status_code == 200
    f = r.json()
    assert {"value": "Finance", "count": 2} in f["domains"] and all(d["value"] != "Research" for d in f["domains"])
    assert {"value": "Delhi", "count": 2} in f["locations"]
    assert {"value": "REMOTE", "count": 2} in f["work_modes"]
    assert f["companies"] == [{"id": str(c.id), "name": "Facet Co", "count": 3}]
    assert f["stipend"] == {"min": 5000.0, "max": 9000.0}


# ---- detail, saved, recommendations ----------------------------------------------------------------------------------


async def test_detail_visibility_and_student_flags(client, db):
    fac = await make_faculty(db)
    student = await make_student(db)
    applicant = await make_student(db)
    h = auth_headers(student)
    draft = await make_internship(db, fac, status="DRAFT")
    assert (await client.get(f"{URL}/{draft.id}", headers=h)).status_code == 404
    it = await make_internship(db, fac)
    r = await client.get(f"{URL}/{it.id}", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert d["can_apply"] is True and d["my_application"] is None and d["can_edit"] is False
    assert d["rejection_reason"] is None and d["application_count"] is None
    await make_application(db, applicant, it)
    d = (await client.get(f"{URL}/{it.id}", headers=auth_headers(applicant))).json()
    assert d["can_apply"] is False and d["my_application"]["status"] == "PENDING"
    # owner sees count and can edit
    d = (await client.get(f"{URL}/{it.id}", headers=auth_headers(fac))).json()
    assert d["application_count"] == 1 and d["can_edit"] is True
    # a student who applied can still open it after it is closed/archived
    it.status = "CLOSED"
    await db.flush()
    assert (await client.get(f"{URL}/{it.id}", headers=auth_headers(applicant))).status_code == 200


async def test_save_unsave_and_saved_list(client, db):
    fac = await make_faculty(db)
    student = await make_student(db)
    h = auth_headers(student)
    it = await make_internship(db, fac)
    other = await make_internship(db, fac)
    assert (await client.post(f"{URL}/{it.id}/save", headers=auth_headers(fac))).status_code == 403
    assert (await client.post(f"{URL}/{it.id}/save", headers=h)).json() == {"is_saved": True}
    assert (await client.post(f"{URL}/{it.id}/save", headers=h)).status_code == 200  # idempotent
    r = await client.get(f"{URL}/saved", headers=h)
    assert ids(r) == [str(it.id)] and r.json()["items"][0]["is_saved"] is True
    assert (await client.get(f"{URL}/{it.id}", headers=h)).json()["is_saved"] is True
    assert (await client.get(f"{URL}/{other.id}", headers=h)).json()["is_saved"] is False
    assert (await client.delete(f"{URL}/{it.id}/save", headers=h)).json() == {"is_saved": False}
    assert ids(await client.get(f"{URL}/saved", headers=h)) == []
    draft = await make_internship(db, fac, status="DRAFT")
    assert (await client.post(f"{URL}/{draft.id}/save", headers=h)).status_code == 404


async def test_recommended_and_similar(client, db):
    fac = await make_faculty(db)
    student = await make_student(db, department="CSE", gpa="3.0")
    student.profile.skills = ["Python", "SQL"]
    await db.flush()
    h = auth_headers(student)
    match = await make_internship(db, fac, skills=["Python", "SQL"], domain="Data Science")
    partial = await make_internship(db, fac, skills=["Python", "Go"], domain="Cloud & DevOps")
    gpa_gate = await make_internship(db, fac, skills=["Python"], min_gpa="3.8")
    dept_gate = await make_internship(db, fac, skills=["Python"], eligible_departments=["Mechanical"])
    applied = await make_internship(db, fac, skills=["Python", "SQL"])
    await make_application(db, student, applied)
    r = await client.get(f"{URL}/recommended", headers=h)
    assert r.status_code == 200
    got = [i["id"] for i in r.json()]
    assert got[0] == str(match.id) and str(partial.id) in got
    assert str(gpa_gate.id) not in got and str(dept_gate.id) not in got and str(applied.id) not in got
    assert (await client.get(f"{URL}/recommended", headers=auth_headers(fac))).status_code == 403

    sim = await client.get(f"{URL}/{match.id}/similar", headers=h)
    assert sim.status_code == 200
    sim_ids = [i["id"] for i in sim.json()]
    assert str(match.id) not in sim_ids and str(partial.id) in sim_ids


async def test_internship_applications_listing(client, db):
    fac = await make_faculty(db)
    other = await make_faculty(db)
    s1, s2 = await make_student(db, full_name="Alice Applicant"), await make_student(db, full_name="Bob Builder")
    it = await make_internship(db, fac)
    await make_application(db, s1, it)
    await make_application(db, s2, it, status="SHORTLISTED")
    r = await client.get(f"{URL}/{it.id}/applications", headers=auth_headers(fac))
    assert r.status_code == 200 and r.json()["total"] == 2
    r = await client.get(f"{URL}/{it.id}/applications", headers=auth_headers(fac), params={"status": "SHORTLISTED"})
    assert [a["student"]["full_name"] for a in r.json()["items"]] == ["Bob Builder"]
    r = await client.get(f"{URL}/{it.id}/applications", headers=auth_headers(fac), params={"q": "alice"})
    assert r.json()["total"] == 1
    assert (await client.get(f"{URL}/{it.id}/applications", headers=auth_headers(other))).status_code == 404
    assert (await client.get(f"{URL}/{it.id}/applications", headers=auth_headers(s1))).status_code == 403


async def test_requires_auth(client):
    assert (await client.get(URL)).status_code == 401
    assert (await client.get(f"{URL}/facets")).status_code == 401


async def test_orm_roundtrip_sanity(db):
    fac = await make_faculty(db)
    it = await make_internship(db, fac)
    row = (await db.execute(select(Internship).where(Internship.id == it.id))).scalar_one()
    assert row.duration_weeks == 12
