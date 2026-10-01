"""Documents center: presigned upload flow, PDF/size validation, scoping, delete, verification (plan 4.4, V4)."""

import uuid

import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.modules.documents import service as documents_service
from app.modules.documents.models import Document
from app.modules.notifications.models import Notification
from tests.factories import (
    auth_headers,
    make_admin,
    make_application,
    make_company_user,
    make_faculty,
    make_internship,
    make_resume,
    make_student,
)

URL = "/api/v1/documents"
PDF_BYTES = b"%PDF-1.7\n%fake pdf body\n" + b"0" * 200
MAX = 5_242_880


def body(**over):
    b = {"kind": "RESUME", "filename": "My Resume (final).pdf", "content_type": "application/pdf", "size_bytes": len(PDF_BYTES)}
    b.update(over)
    return b


async def request_upload(client, user, **over):
    r = await client.post(f"{URL}/upload-url", headers=auth_headers(user), json=body(**over))
    return r


async def doc_key(db, document_id) -> str:
    return (await db.execute(select(Document.object_key).where(Document.id == uuid.UUID(document_id)))).scalar_one()


# ---- upload-url ----------------------------------------------------------------------------------------------------
async def test_upload_url_returns_ticket(client, db):
    student = await make_student(db)
    r = await request_upload(client, student)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["max_bytes"] == MAX and data["expires_in"] > 0
    assert data["upload"]["url"] and data["upload"]["fields"]["Content-Type"] == "application/pdf"
    doc = (await db.execute(select(Document).where(Document.id == uuid.UUID(data["document_id"])))).scalar_one()
    assert doc.status == "PENDING_UPLOAD" and doc.bucket == "resumes" and doc.owner_id == student.id
    assert doc.object_key.startswith(f"{student.id}/{doc.id}/") and doc.object_key.endswith("My-Resume-final.pdf")


async def test_upload_url_requires_auth(client):
    assert (await client.post(f"{URL}/upload-url", json=body())).status_code == 401


@pytest.mark.parametrize("ctype", ["image/png", "application/msword", "text/plain"])
async def test_upload_url_rejects_non_pdf(client, db, ctype):
    student = await make_student(db)
    r = await request_upload(client, student, content_type=ctype)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "RESUME_INVALID"


async def test_upload_url_rejects_over_5mb(client, db):
    student = await make_student(db)
    r = await request_upload(client, student, size_bytes=MAX + 1)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "FILE_TOO_LARGE"
    assert (await request_upload(client, student, size_bytes=MAX)).status_code == 200  # boundary is allowed


async def test_upload_url_rejects_empty_and_bad_kind(client, db):
    student = await make_student(db)
    assert (await request_upload(client, student, size_bytes=0)).status_code == 422
    assert (await request_upload(client, student, kind="NOPE")).status_code == 422
    assert (await request_upload(client, student, kind="REPORT")).status_code == 422  # worker-generated only


async def test_upload_url_non_resume_kind_allows_images(client, db):
    student = await make_student(db)
    r = await request_upload(client, student, kind="TRANSCRIPT", content_type="image/png", filename="t.png")
    assert r.status_code == 200
    doc = (await db.execute(select(Document).where(Document.id == uuid.UUID(r.json()["document_id"])))).scalar_one()
    assert doc.bucket == "documents"


# ---- complete -------------------------------------------------------------------------------------------------------
async def test_complete_happy_path_and_idempotent(client, db, fake_storage):
    student = await make_student(db, full_name="Dana Doc")
    doc_id = (await request_upload(client, student)).json()["document_id"]
    fake_storage.put(await doc_key(db, doc_id), PDF_BYTES)
    r = await client.post(f"{URL}/{doc_id}/complete", headers=auth_headers(student))
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "UPLOADED" and out["verification_status"] == "PENDING" and out["in_use"] is False
    assert out["owner"] == {"id": str(student.id), "full_name": "Dana Doc"}
    assert out["size_bytes"] == len(PDF_BYTES) and out["kind"] == "RESUME"
    again = await client.post(f"{URL}/{doc_id}/complete", headers=auth_headers(student))
    assert again.status_code == 200 and again.json()["id"] == doc_id


async def test_complete_rejects_bad_magic(client, db, fake_storage):
    student = await make_student(db)
    doc_id = (await request_upload(client, student, size_bytes=64)).json()["document_id"]
    key = await doc_key(db, doc_id)
    fake_storage.put(key, b"MZ\x90\x00" + b"x" * 60)  # an .exe pretending to be a PDF
    r = await client.post(f"{URL}/{doc_id}/complete", headers=auth_headers(student))
    assert r.status_code == 422 and r.json()["error"]["code"] == "RESUME_INVALID"
    assert not fake_storage.has(key)  # object removed
    doc = (await db.execute(select(Document).where(Document.id == uuid.UUID(doc_id)))).scalar_one()
    await db.refresh(doc)
    assert doc.status == "REJECTED"  # persisted even though the request failed
    retry = await client.post(f"{URL}/{doc_id}/complete", headers=auth_headers(student))
    assert retry.status_code == 409


async def test_complete_rejects_size_mismatch(client, db, fake_storage):
    student = await make_student(db)
    doc_id = (await request_upload(client, student, size_bytes=1000)).json()["document_id"]
    fake_storage.put(await doc_key(db, doc_id), PDF_BYTES)  # real size != declared 1000
    r = await client.post(f"{URL}/{doc_id}/complete", headers=auth_headers(student))
    assert r.status_code == 422 and r.json()["error"]["code"] == "RESUME_INVALID"


async def test_complete_rejects_oversized_object(client, db, fake_storage):
    student = await make_student(db)
    doc_id = (await request_upload(client, student)).json()["document_id"]
    fake_storage.put(await doc_key(db, doc_id), b"%PDF-" + b"0" * MAX)  # MAX + 5 bytes
    r = await client.post(f"{URL}/{doc_id}/complete", headers=auth_headers(student))
    assert r.status_code == 422 and r.json()["error"]["code"] == "FILE_TOO_LARGE"


async def test_complete_rejects_wrong_stored_content_type(client, db, fake_storage):
    student = await make_student(db)
    doc_id = (await request_upload(client, student)).json()["document_id"]
    fake_storage.put(await doc_key(db, doc_id), PDF_BYTES, content_type="application/octet-stream")
    r = await client.post(f"{URL}/{doc_id}/complete", headers=auth_headers(student))
    assert r.status_code == 422


async def test_complete_without_object_is_422_and_retryable(client, db, fake_storage):
    student = await make_student(db)
    doc_id = (await request_upload(client, student)).json()["document_id"]
    r = await client.post(f"{URL}/{doc_id}/complete", headers=auth_headers(student))
    assert r.status_code == 422
    fake_storage.put(await doc_key(db, doc_id), PDF_BYTES)
    assert (await client.post(f"{URL}/{doc_id}/complete", headers=auth_headers(student))).status_code == 200


async def test_complete_only_owner(client, db, fake_storage):
    owner, other = await make_student(db), await make_student(db)
    admin = await make_admin(db)
    doc_id = (await request_upload(client, owner)).json()["document_id"]
    fake_storage.put(await doc_key(db, doc_id), PDF_BYTES)
    assert (await client.post(f"{URL}/{doc_id}/complete", headers=auth_headers(other))).status_code == 404
    assert (await client.post(f"{URL}/{doc_id}/complete", headers=auth_headers(admin))).status_code == 404
    assert (await client.post(f"{URL}/{uuid.uuid4()}/complete", headers=auth_headers(owner))).status_code == 404


# ---- list -----------------------------------------------------------------------------------------------------------
async def test_list_scoped_to_owner_admin_sees_all(client, db):
    a, b = await make_student(db), await make_student(db)
    admin = await make_admin(db)
    ra, rb = await make_resume(db, a), await make_resume(db, b)
    await make_resume(db, a, status="PENDING_UPLOAD")  # hidden by default

    mine = (await client.get(URL, headers=auth_headers(a))).json()
    assert [d["id"] for d in mine["items"]] == [str(ra.id)] and mine["total"] == 1
    # asking for someone else's documents yields nothing, not an error
    other = (await client.get(URL, headers=auth_headers(a), params={"owner_id": str(b.id)})).json()
    assert other["total"] == 0
    everything = (await client.get(URL, headers=auth_headers(admin))).json()
    assert {d["id"] for d in everything["items"]} >= {str(ra.id), str(rb.id)}
    only_b = (await client.get(URL, headers=auth_headers(admin), params={"owner_id": str(b.id)})).json()
    assert [d["id"] for d in only_b["items"]] == [str(rb.id)]


async def test_list_filters(client, db):
    a = await make_student(db)
    admin = await make_admin(db)
    v = await make_resume(db, a, verification_status="VERIFIED")
    await make_resume(db, a)
    r = await client.get(URL, headers=auth_headers(admin), params={"owner_id": str(a.id), "verification_status": "VERIFIED"})
    assert [d["id"] for d in r.json()["items"]] == [str(v.id)]
    r = await client.get(URL, headers=auth_headers(a), params={"kind": "TRANSCRIPT"})
    assert r.json()["total"] == 0
    assert (await client.get(URL, headers=auth_headers(a), params={"kind": "BAD"})).status_code == 422


# ---- download-url ---------------------------------------------------------------------------------------------------
async def test_download_url_scoping(client, db):
    student, other_student = await make_student(db), await make_student(db)
    admin = await make_admin(db)
    fac_a, fac_b = await make_faculty(db), await make_faculty(db)
    comp = await make_company_user(db)
    other_comp = await make_company_user(db)
    internship_a = await make_internship(db, fac_a)
    internship_c = await make_internship(db, comp, company=comp.company)
    resume = await make_resume(db, student)
    await make_application(db, student, internship_a, resume=resume)
    url = f"{URL}/{resume.id}/download-url"

    for allowed in (student, admin, fac_a):
        r = await client.get(url, headers=auth_headers(allowed))
        assert r.status_code == 200, (allowed.role, r.text)
        assert r.json()["expires_in"] == 300 and "fake-storage" in r.json()["url"]
    for denied in (other_student, fac_b, comp, other_comp):
        assert (await client.get(url, headers=auth_headers(denied))).status_code == 404

    # a company member sees resumes of applicants to its own internships
    resume2 = await make_resume(db, other_student)
    await make_application(db, other_student, internship_c, resume=resume2)
    assert (await client.get(f"{URL}/{resume2.id}/download-url", headers=auth_headers(comp))).status_code == 200
    assert (await client.get(f"{URL}/{resume2.id}/download-url", headers=auth_headers(other_comp))).status_code == 404


async def test_download_url_pending_upload_conflict(client, db):
    student = await make_student(db)
    doc = await make_resume(db, student, status="PENDING_UPLOAD")
    r = await client.get(f"{URL}/{doc.id}/download-url", headers=auth_headers(student))
    assert r.status_code == 409


# ---- delete ---------------------------------------------------------------------------------------------------------
async def test_delete_unused_document_clears_default_and_object(client, db, fake_storage):
    student = await make_student(db)
    resume = await make_resume(db, student)
    fake_storage.put(resume.object_key, PDF_BYTES)
    student.profile.default_resume_id = resume.id
    await db.flush()
    r = await client.delete(f"{URL}/{resume.id}", headers=auth_headers(student))
    assert r.status_code == 204
    assert not fake_storage.has(resume.object_key)
    await db.refresh(resume)
    await db.refresh(student.profile)
    assert resume.deleted_at is not None and student.profile.default_resume_id is None
    assert (await client.get(f"{URL}/{resume.id}/download-url", headers=auth_headers(student))).status_code == 404
    assert (await client.get(URL, headers=auth_headers(student))).json()["total"] == 0


async def test_delete_blocked_when_used_by_active_application(client, db):
    student = await make_student(db)
    owner = await make_faculty(db)
    internship = await make_internship(db, owner)
    resume = await make_resume(db, student)
    app = await make_application(db, student, internship, resume=resume)
    r = await client.delete(f"{URL}/{resume.id}", headers=auth_headers(student))
    assert r.status_code == 409 and r.json()["error"]["code"] == "IN_USE"
    listed = (await client.get(URL, headers=auth_headers(student))).json()["items"][0]
    assert listed["in_use"] is True
    # once the application is withdrawn the document can go (the object is kept for the old application)
    app.status = "WITHDRAWN"
    await db.flush()
    assert (await client.delete(f"{URL}/{resume.id}", headers=auth_headers(student))).status_code == 204


async def test_delete_other_users_document_404_admin_ok(client, db):
    owner, other = await make_student(db), await make_student(db)
    admin = await make_admin(db)
    d1, d2 = await make_resume(db, owner), await make_resume(db, owner)
    assert (await client.delete(f"{URL}/{d1.id}", headers=auth_headers(other))).status_code == 404
    assert (await client.delete(f"{URL}/{d1.id}", headers=auth_headers(admin))).status_code == 204
    assert (await client.delete(f"{URL}/{d2.id}", headers=auth_headers(owner))).status_code == 204
    assert (await client.delete(f"{URL}/{d2.id}", headers=auth_headers(owner))).status_code == 404


# ---- verification (admin) ----------------------------------------------------------------------------------------------
async def test_verification_admin_only_and_notifies(client, db):
    student, fac = await make_student(db), await make_faculty(db)
    admin = await make_admin(db)
    resume = await make_resume(db, student)
    payload = {"verification_status": "VERIFIED", "note": "Looks good"}
    for who in (student, fac):
        assert (await client.patch(f"{URL}/{resume.id}/verification", headers=auth_headers(who), json=payload)).status_code == 403
    r = await client.patch(f"{URL}/{resume.id}/verification", headers=auth_headers(admin), json=payload)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["verification_status"] == "VERIFIED" and out["verification_note"] == "Looks good" and out["verified_at"]
    note = (await db.execute(select(Notification).where(Notification.user_id == student.id))).scalars().all()
    assert len(note) == 1 and "verified" in note[0].title.lower()
    bad = await client.patch(
        f"{URL}/{resume.id}/verification", headers=auth_headers(admin), json={"verification_status": "MAYBE"}
    )
    assert bad.status_code == 422
    pending = await make_resume(db, student, status="PENDING_UPLOAD")
    r = await client.patch(f"{URL}/{pending.id}/verification", headers=auth_headers(admin), json=payload)
    assert r.status_code == 409


# ---- reusable resume validation (used by applications / students) ---------------------------------------------------------
async def test_validate_resume_document_rules(db):
    student, other = await make_student(db), await make_student(db)
    good = await make_resume(db, student)
    assert (await documents_service.validate_resume_document(db, student.id, good.id)).id == good.id

    async def code(doc_id, owner=student):
        with pytest.raises(AppError) as exc:
            await documents_service.validate_resume_document(db, owner.id, doc_id)
        assert exc.value.status_code == 422
        return exc.value.code

    assert await code(None) == "RESUME_REQUIRED"
    assert await code(uuid.uuid4()) == "RESUME_INVALID"
    assert await code(good.id, owner=other) == "RESUME_INVALID"  # foreign resume
    assert await code((await make_resume(db, student, status="PENDING_UPLOAD")).id) == "RESUME_INVALID"
    assert await code((await make_resume(db, student, status="REJECTED")).id) == "RESUME_INVALID"
    other_kind = Document(
        id=uuid.uuid4(), owner_id=student.id, kind="TRANSCRIPT", bucket="documents", object_key=f"k/{uuid.uuid4()}",
        filename="t.pdf", content_type="application/pdf", size_bytes=10, status="UPLOADED",
    )
    db.add(other_kind)
    await db.flush()
    assert await code(other_kind.id) == "RESUME_INVALID"
