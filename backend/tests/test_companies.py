"""Companies: registration number rules (V11), CRUD, approval, archive/restore, hard delete, ratings, visibility."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.modules.admin.models import AuditLog
from app.modules.companies.models import Company
from app.modules.documents.models import Document
from app.modules.feedback.models import StudentFeedback
from app.modules.internships.models import SavedInternship
from app.modules.notifications.models import Notification
from tests.factories import (
    auth_headers,
    make_admin,
    make_application,
    make_company,
    make_company_user,
    make_faculty,
    make_internship,
    make_student,
    unique_cin,
)

URL = "/api/v1/companies"
VALID_CIN = "U72200KA2015PTC082345"


def payload(**over):
    p = {
        "name": "Acme Robotics",
        "registration_number": VALID_CIN,
        "location": "Bengaluru, India",
        "industry": "Robotics",
        "website": "https://acme.example.com",
        "description": "We build robots.",
        "contact_person_name": "Wile E",
        "contact_email": "Hr@Acme.example.com",
        "contact_phone": "+91 98765 43210",
    }
    p.update(over)
    return p


async def add_feedback(db, student, company, internship, application, overall, *, anonymous=False, comments=None, dims=(5, 4, 3, 2)):
    db.add(
        StudentFeedback(
            application_id=application.id,
            student_id=student.id,
            company_id=company.id,
            internship_id=internship.id,
            company_culture=dims[0],
            mentorship=dims[1],
            technical_learning=dims[2],
            work_environment=dims[3],
            overall=overall,
            comments=comments,
            is_anonymous=anonymous,
        )
    )
    await db.flush()


# ---- create / registration number ----------------------------------------------------------------------------------
async def test_create_company_admin_and_faculty(client, db):
    admin, fac = await make_admin(db), await make_faculty(db)
    r = await client.post(URL, headers=auth_headers(admin), json=payload())
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["status"] == "ACTIVE" and c["registration_number"] == VALID_CIN
    assert c["contact_email"] == "hr@acme.example.com" and c["contact_phone"] == "+919876543210"
    assert c["rating_summary"] == {
        "count": 0, "overall": None, "company_culture": None, "mentorship": None, "technical_learning": None,
        "work_environment": None, "distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
    }
    assert c["avg_rating"] is None and c["rating_count"] == 0 and c["open_internships"] == 0 and c["internship_count"] == 0
    assert c["logo_url"] is None and c["archived_at"] is None
    row = (await db.execute(select(Company).where(Company.id == uuid.UUID(c["id"])))).scalar_one()
    assert row.created_by == admin.id
    audit = (await db.execute(select(AuditLog).where(AuditLog.action == "company.create"))).scalars().all()
    assert len(audit) == 1 and str(audit[0].entity_id) == c["id"]
    r = await client.post(URL, headers=auth_headers(fac), json=payload(registration_number="US-DE5567123"))
    assert r.status_code == 201 and r.json()["status"] == "ACTIVE"


@pytest.mark.parametrize("role", ["STUDENT", "COMPANY"])
async def test_create_company_forbidden(client, db, role):
    user = await (make_student(db) if role == "STUDENT" else make_company_user(db))
    assert (await client.post(URL, headers=auth_headers(user), json=payload())).status_code == 403
    assert (await client.post(URL, json=payload())).status_code == 401


@pytest.mark.parametrize(
    ("raw", "stored"),
    [
        ("U72200KA2015PTC082345", "U72200KA2015PTC082345"),
        ("L17110MH1973PLC019786", "L17110MH1973PLC019786"),
        ("US-DE5567123", "US-DE5567123"),
        ("gb-ab12cd34", "GB-AB12CD34"),  # normalised to upper case
        (" u72200ka2015ptc082346 ", "U72200KA2015PTC082346"),
        ("US - DE5567123 ", "US-DE5567123"),  # spaces stripped
    ],
)
async def test_reg_number_formats_valid(client, db, raw, stored):
    admin = await make_admin(db)
    r = await client.post(URL, headers=auth_headers(admin), json=payload(registration_number=raw))
    assert r.status_code == 201, r.text
    assert r.json()["registration_number"] == stored


@pytest.mark.parametrize(
    "raw", ["ABC", "", "12345678901234567890A", "U72200KA2015PTC08234", "U72200KA2015PTC0823456", "A-123456", "USA-DE5567123", "US-DE55", "US_DE5567123"]
)
async def test_reg_number_formats_invalid(client, db, raw):
    admin = await make_admin(db)
    r = await client.post(URL, headers=auth_headers(admin), json=payload(registration_number=raw))
    assert r.status_code == 422, raw
    assert r.json()["error"]["details"][0]["field"] == "registration_number"


async def test_reg_number_duplicate_409(client, db):
    admin = await make_admin(db)
    assert (await client.post(URL, headers=auth_headers(admin), json=payload())).status_code == 201
    r = await client.post(URL, headers=auth_headers(admin), json=payload(name="Other", registration_number=VALID_CIN.lower()))
    assert r.status_code == 409 and r.json()["error"]["code"] == "DUPLICATE_REGISTRATION_NUMBER"


@pytest.mark.parametrize(
    "over",
    [
        {"name": "A"},
        {"location": ""},
        {"contact_person_name": "x"},
        {"contact_email": "nope"},
        {"contact_phone": "123"},
        {"website": "acme.com"},
    ],
)
async def test_create_company_validation_422(client, db, over):
    admin = await make_admin(db)
    assert (await client.post(URL, headers=auth_headers(admin), json=payload(**over))).status_code == 422


async def test_create_company_with_logo_document(client, db):
    admin = await make_admin(db)
    logo = Document(
        id=uuid.uuid4(), owner_id=admin.id, kind="LOGO", bucket="documents", object_key=f"k/{uuid.uuid4()}",
        filename="logo.png", content_type="image/png", size_bytes=100, status="UPLOADED",
    )
    notlogo = Document(
        id=uuid.uuid4(), owner_id=admin.id, kind="OTHER", bucket="documents", object_key=f"k/{uuid.uuid4()}",
        filename="x.png", content_type="image/png", size_bytes=100, status="UPLOADED",
    )
    db.add_all([logo, notlogo])
    await db.flush()
    r = await client.post(URL, headers=auth_headers(admin), json=payload(logo_document_id=str(logo.id)))
    assert r.status_code == 201 and "fake-storage" in r.json()["logo_url"]
    bad = await client.post(
        URL, headers=auth_headers(admin), json=payload(registration_number=unique_cin(), logo_document_id=str(notlogo.id))
    )
    assert bad.status_code == 422
    assert (await client.get(URL, headers=auth_headers(admin), params={"q": "Acme"})).json()["items"][0]["logo_url"]


# ---- read / list / visibility -----------------------------------------------------------------------------------------
async def test_list_visibility_per_role(client, db):
    admin, fac, other_fac = await make_admin(db), await make_faculty(db), await make_faculty(db)
    student = await make_student(db)
    active = await make_company(db, name="Visible Co")
    pending = await make_company(db, name="Pending Co", status="PENDING", created_by=fac)
    archived = await make_company(db, name="Archived Co", status="ARCHIVED")
    own = await make_company_user(db, await make_company(db, name="Own Pending Co", status="PENDING"))

    def names(resp):
        return {i["name"] for i in resp.json()["items"]}

    assert {"Visible Co", "Pending Co", "Archived Co", "Own Pending Co"} <= names(await client.get(URL, headers=auth_headers(admin)))
    s = names(await client.get(URL, headers=auth_headers(student)))
    assert "Visible Co" in s and not s & {"Pending Co", "Archived Co", "Own Pending Co"}
    f = names(await client.get(URL, headers=auth_headers(fac)))
    assert "Pending Co" in f and "Archived Co" not in f and "Own Pending Co" not in f
    assert "Pending Co" not in names(await client.get(URL, headers=auth_headers(other_fac)))
    c = names(await client.get(URL, headers=auth_headers(own)))
    assert "Own Pending Co" in c and "Pending Co" not in c and "Visible Co" in c

    # detail follows the same rules: outside scope is 404
    assert (await client.get(f"{URL}/{active.id}", headers=auth_headers(student))).status_code == 200
    for hidden in (pending, archived):
        assert (await client.get(f"{URL}/{hidden.id}", headers=auth_headers(student))).status_code == 404
        assert (await client.get(f"{URL}/{hidden.id}", headers=auth_headers(admin))).status_code == 200
    assert (await client.get(f"{URL}/{pending.id}", headers=auth_headers(fac))).status_code == 200
    assert (await client.get(f"{URL}/{pending.id}", headers=auth_headers(other_fac))).status_code == 404
    assert (await client.get(f"{URL}/{uuid.uuid4()}", headers=auth_headers(admin))).status_code == 404
    assert (await client.get(URL)).status_code == 401


async def test_list_filters_and_pagination(client, db):
    admin = await make_admin(db)
    await make_company(db, name="Zebra Systems", location="Pune, India", industry="Fintech")
    await make_company(db, name="Zebra Labs", location="Austin, US", industry="Biotech")
    await make_company(db, name="Other Co", status="ARCHIVED")
    h = auth_headers(admin)
    assert (await client.get(URL, headers=h, params={"q": "zebra"})).json()["total"] == 2
    assert (await client.get(URL, headers=h, params={"q": "zebra", "location": "pune"})).json()["total"] == 1
    assert (await client.get(URL, headers=h, params={"q": "zebra", "industry": "Biotech"})).json()["items"][0]["name"] == "Zebra Labs"
    assert (await client.get(URL, headers=h, params={"status": "ARCHIVED", "q": "other"})).json()["total"] == 1
    assert (await client.get(URL, headers=h, params={"status": "BOGUS"})).status_code == 422
    r = (await client.get(URL, headers=h, params={"q": "zebra", "page_size": 1, "page": 2})).json()
    assert r["total"] == 2 and r["pages"] == 2 and len(r["items"]) == 1 and r["page"] == 2
    assert (await client.get(URL, headers=h, params={"q": "50%"})).json()["total"] == 0


async def test_detail_with_rating_summary_and_open_internships(client, db):
    admin, fac = await make_admin(db), await make_faculty(db)
    company = await make_company(db, name="Rated Co")
    students = [await make_student(db) for _ in range(3)]
    internship = await make_internship(db, fac, company=company)
    await make_internship(db, fac, company=company, status="DRAFT")
    await make_internship(db, fac, company=company, deadline_in_days=-3)  # expired -> not "open"
    for st, overall in zip(students, (5, 4, 4), strict=True):
        app = await make_application(db, st, internship, status="ACCEPTED")
        await add_feedback(db, st, company, internship, app, overall)
    r = await client.get(f"{URL}/{company.id}", headers=auth_headers(admin))
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["rating_count"] == 3 and c["avg_rating"] == 4.33 and c["open_internships"] == 1 and c["internship_count"] == 3
    rs = c["rating_summary"]
    assert rs["count"] == 3 and rs["overall"] == 4.33
    assert (rs["company_culture"], rs["mentorship"], rs["technical_learning"], rs["work_environment"]) == (5.0, 4.0, 3.0, 2.0)
    assert rs["distribution"] == {"1": 0, "2": 0, "3": 0, "4": 2, "5": 1}
    listed = (await client.get(URL, headers=auth_headers(admin), params={"q": "Rated"})).json()["items"][0]
    assert listed["avg_rating"] == 4.33 and listed["rating_count"] == 3 and listed["open_internships"] == 1
    assert "contact_email" not in listed  # summary rows stay light


async def test_ratings_endpoint_anonymises(client, db):
    admin, fac = await make_admin(db), await make_faculty(db)
    viewer = await make_student(db)
    company = await make_company(db)
    internship = await make_internship(db, fac, company=company, title="Backend Intern")
    named, hidden = await make_student(db, full_name="Nora Named"), await make_student(db, full_name="Anon Ymous")
    app1 = await make_application(db, named, internship, status="ACCEPTED")
    app2 = await make_application(db, hidden, internship, status="ACCEPTED")
    await add_feedback(db, named, company, internship, app1, 5, comments="Great mentors")
    await add_feedback(db, hidden, company, internship, app2, 2, anonymous=True, comments="Too much overtime")
    r = await client.get(f"{URL}/{company.id}/ratings", headers=auth_headers(viewer))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["count"] == 2 and body["summary"]["overall"] == 3.5
    by_comment = {x["comments"]: x for x in body["recent"]}
    assert by_comment["Great mentors"]["student_name"] == "Nora Named"
    assert by_comment["Too much overtime"]["student_name"] is None
    assert by_comment["Great mentors"]["internship_title"] == "Backend Intern"
    adm = (await client.get(f"{URL}/{company.id}/ratings", headers=auth_headers(admin))).json()
    assert {x["student_name"] for x in adm["recent"]} == {"Nora Named", "Anon Ymous"}
    empty = (await client.get(f"{URL}/{(await make_company(db)).id}/ratings", headers=auth_headers(viewer))).json()
    assert empty["summary"]["count"] == 0 and empty["recent"] == []


# ---- update ------------------------------------------------------------------------------------------------------------
async def test_update_permissions(client, db):
    admin = await make_admin(db)
    creator, other_fac = await make_faculty(db), await make_faculty(db)
    student = await make_student(db)
    company = await make_company(db, name="Edit Me", created_by=creator)
    member = await make_company_user(db, company)
    outsider = await make_company_user(db)
    url = f"{URL}/{company.id}"
    patch = {"description": "Updated", "industry": None, "contact_phone": "9876543210"}

    for who in (admin, creator, member):
        r = await client.patch(url, headers=auth_headers(who), json={"description": f"By {who.role}"})
        assert r.status_code == 200 and r.json()["description"] == f"By {who.role}"
    r = await client.patch(url, headers=auth_headers(admin), json=patch)
    assert r.json()["industry"] is None and r.json()["contact_phone"] == "9876543210" and r.json()["name"] == "Edit Me"
    assert (await client.patch(url, headers=auth_headers(other_fac), json={"name": "Hax"})).status_code == 403
    assert (await client.patch(url, headers=auth_headers(outsider), json={"name": "Hax"})).status_code == 403
    assert (await client.patch(url, headers=auth_headers(student), json={"name": "Hax"})).status_code == 403
    assert (await client.patch(url, json={"name": "Hax"})).status_code == 401
    assert (await client.patch(f"{URL}/{uuid.uuid4()}", headers=auth_headers(admin), json={"name": "Hax"})).status_code == 404
    # name cannot be nulled (NOT NULL column); invalid values are rejected
    assert (await client.patch(url, headers=auth_headers(admin), json={"name": None})).json()["name"] == "Edit Me"
    assert (await client.patch(url, headers=auth_headers(admin), json={"contact_email": "bad"})).status_code == 422
    assert (await client.patch(url, headers=auth_headers(admin), json={"registration_number": "ABC"})).status_code == 422
    audit = (await db.execute(select(AuditLog).where(AuditLog.action == "company.update"))).scalars().all()
    assert len(audit) >= 4 and audit[0].before is not None


async def test_registration_number_change_rules(client, db):
    admin = await make_admin(db)
    member = await make_company_user(db)
    other = await make_company(db, registration_number="US-TAKEN123")
    url = f"{URL}/{member.company.id}"
    same = member.company.registration_number
    assert (await client.patch(url, headers=auth_headers(member), json={"registration_number": same.lower()})).status_code == 200
    assert (await client.patch(url, headers=auth_headers(member), json={"registration_number": "US-NEWNUM99"})).status_code == 403
    r = await client.patch(url, headers=auth_headers(admin), json={"registration_number": "US-NEWNUM99"})
    assert r.status_code == 200 and r.json()["registration_number"] == "US-NEWNUM99"
    r = await client.patch(url, headers=auth_headers(admin), json={"registration_number": other.registration_number})
    assert r.status_code == 409 and r.json()["error"]["code"] == "DUPLICATE_REGISTRATION_NUMBER"


# ---- approve / archive / restore / delete --------------------------------------------------------------------------------------
async def test_approve_flow(client, db):
    admin, fac = await make_admin(db), await make_faculty(db)
    company = await make_company(db, status="PENDING")
    member = await make_company_user(db, company)
    url = f"{URL}/{company.id}/approve"
    for who in (fac, member):
        assert (await client.post(url, headers=auth_headers(who))).status_code == 403
    r = await client.post(url, headers=auth_headers(admin))
    assert r.status_code == 200 and r.json()["status"] == "ACTIVE"
    notes = (await db.execute(select(Notification).where(Notification.user_id == member.id))).scalars().all()
    assert len(notes) == 1 and "approved" in notes[0].title.lower()
    again = await client.post(url, headers=auth_headers(admin))
    assert again.status_code == 409 and again.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
    assert (await client.post(f"{URL}/{uuid.uuid4()}/approve", headers=auth_headers(admin))).status_code == 404


async def test_archive_and_restore(client, db):
    admin, fac, student = await make_admin(db), await make_faculty(db), await make_student(db)
    company = await make_company(db, name="Arc Co")
    base = f"{URL}/{company.id}"
    for who in (fac, student):
        assert (await client.post(f"{base}/archive", headers=auth_headers(who))).status_code == 403
        assert (await client.post(f"{base}/restore", headers=auth_headers(who))).status_code == 403
    assert (await client.post(f"{base}/restore", headers=auth_headers(admin))).status_code == 409  # not archived

    r = await client.post(f"{base}/archive", headers=auth_headers(admin))
    assert r.status_code == 200 and r.json()["status"] == "ARCHIVED" and r.json()["archived_at"]
    assert (await client.post(f"{base}/archive", headers=auth_headers(admin))).status_code == 409
    assert (await client.get(base, headers=auth_headers(student))).status_code == 404  # hidden from students
    assert (await client.get(URL, headers=auth_headers(student), params={"q": "Arc Co"})).json()["total"] == 0

    r = await client.post(f"{base}/restore", headers=auth_headers(admin))
    assert r.status_code == 200 and r.json()["status"] == "ACTIVE" and r.json()["archived_at"] is None
    assert (await client.get(base, headers=auth_headers(student))).status_code == 200
    actions = {a.action for a in (await db.execute(select(AuditLog).where(AuditLog.entity_id == company.id))).scalars()}
    assert {"company.archive", "company.restore"} <= actions


async def test_hard_delete_blocked_when_in_use(client, db):
    admin, fac = await make_admin(db), await make_faculty(db)
    used = await make_company(db)
    await make_internship(db, fac, company=used)
    free = await make_company(db)
    r = await client.delete(f"{URL}/{used.id}", headers=auth_headers(admin))
    assert r.status_code == 409 and r.json()["error"]["code"] == "IN_USE"
    assert (await client.delete(f"{URL}/{free.id}", headers=auth_headers(fac))).status_code == 403
    assert (await client.delete(f"{URL}/{free.id}", headers=auth_headers(admin))).status_code == 204
    assert (await client.get(f"{URL}/{free.id}", headers=auth_headers(admin))).status_code == 404
    assert (await client.delete(f"{URL}/{free.id}", headers=auth_headers(admin))).status_code == 404
    assert (await client.get(f"{URL}/{used.id}", headers=auth_headers(admin))).status_code == 200
    audit = (await db.execute(select(AuditLog).where(AuditLog.action == "company.delete"))).scalars().all()
    assert len(audit) == 1


async def test_delete_company_with_members_removes_membership(client, db):
    admin = await make_admin(db)
    member = await make_company_user(db)
    r = await client.delete(f"{URL}/{member.company.id}", headers=auth_headers(admin))
    assert r.status_code == 204


# ---- internships / members ------------------------------------------------------------------------------------------------------
async def test_company_internships_visibility(client, db):
    admin, fac, other_fac = await make_admin(db), await make_faculty(db), await make_faculty(db)
    student = await make_student(db)
    comp_user = await make_company_user(db)
    company = comp_user.company
    open_i = await make_internship(db, fac, company=company, title="Open One")
    draft = await make_internship(db, fac, company=company, status="DRAFT", title="Draft One")
    expired = await make_internship(db, fac, company=company, deadline_in_days=-2, title="Expired One")
    other_draft = await make_internship(db, other_fac, company=company, status="PENDING_APPROVAL", title="Other Pending")
    await make_application(db, student, open_i)
    db.add(SavedInternship(student_id=student.id, internship_id=open_i.id))
    await db.flush()
    url = f"{URL}/{company.id}/internships"

    def titles(resp):
        return {i["title"] for i in resp.json()["items"]}

    r = await client.get(url, headers=auth_headers(student))
    assert r.status_code == 200 and titles(r) == {"Open One"}
    item = r.json()["items"][0]
    assert item["is_saved"] is True and item["application_count"] is None
    assert item["company"]["id"] == str(company.id) and item["stipend_monthly"] == 20000.0
    assert isinstance(item["stipend_monthly"], float)
    assert titles(await client.get(url, headers=auth_headers(admin))) == {"Open One", "Draft One", "Expired One", "Other Pending"}
    assert titles(await client.get(url, headers=auth_headers(fac))) == {"Open One", "Draft One", "Expired One"}
    assert titles(await client.get(url, headers=auth_headers(other_fac))) == {"Open One", "Other Pending"}
    cr = await client.get(url, headers=auth_headers(comp_user))  # company members own every internship of the company
    assert titles(cr) == {"Open One", "Draft One", "Expired One", "Other Pending"}
    counts = {i["title"]: i["application_count"] for i in cr.json()["items"]}
    assert counts["Open One"] == 1 and counts["Draft One"] == 0
    assert draft.id and expired.id and other_draft.id
    assert (await client.get(f"{URL}/{uuid.uuid4()}/internships", headers=auth_headers(admin))).status_code == 404
    arch = await make_company(db, status="ARCHIVED")
    assert (await client.get(f"{URL}/{arch.id}/internships", headers=auth_headers(student))).status_code == 404


async def test_members_endpoint(client, db):
    admin, fac, student = await make_admin(db), await make_faculty(db), await make_student(db)
    m1 = await make_company_user(db, full_name="Mem One")
    company = m1.company
    m2 = await make_company_user(db, company, full_name="Mem Two")
    outsider = await make_company_user(db)
    url = f"{URL}/{company.id}/members"
    r = await client.get(url, headers=auth_headers(admin))
    assert r.status_code == 200
    assert [m["full_name"] for m in r.json()] == ["Mem One", "Mem Two"]
    assert r.json()[0]["job_title"] == "Recruiter" and r.json()[0]["email"] == m1.email
    assert (await client.get(url, headers=auth_headers(m2))).status_code == 200
    assert (await client.get(url, headers=auth_headers(outsider))).status_code == 404  # another company: out of scope
    for who in (fac, student):
        assert (await client.get(url, headers=auth_headers(who))).status_code == 403
    assert (await client.get(f"{URL}/{uuid.uuid4()}/members", headers=auth_headers(admin))).status_code == 404
    assert datetime.now(UTC) - timedelta(days=1) < datetime.now(UTC)
