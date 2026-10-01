import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.db import DB
from app.core.deps import AdminUser, CurrentUser, Pagination
from app.core.pagination import Page
from app.core.ratelimit import rate_limit
from app.core.storage import Storage, get_storage
from app.core.types import DocumentKind
from app.modules.documents import schemas as s
from app.modules.documents import service

router = APIRouter(prefix="/documents", tags=["documents"])

StorageDep = Annotated[Storage, Depends(get_storage)]
_upload_limit = rate_limit("upload-url", 30, 60)


@router.post("/upload-url", response_model=s.UploadTicket, dependencies=[Depends(_upload_limit)])
async def upload_url(db: DB, user: CurrentUser, storage: StorageDep, body: s.UploadUrlRequest):
    return await service.create_upload_url(db, storage, user, body)


@router.get("", response_model=Page[s.Document])
async def list_documents(
    db: DB,
    user: CurrentUser,
    pagination: Pagination,
    kind: Annotated[DocumentKind | None, Query()] = None,
    owner_id: Annotated[uuid.UUID | None, Query()] = None,
    verification_status: Annotated[str | None, Query(pattern="^(PENDING|VERIFIED|REJECTED)$")] = None,
    doc_status: Annotated[str | None, Query(alias="status", pattern="^(PENDING_UPLOAD|UPLOADED|REJECTED)$")] = None,
):
    return await service.list_documents(
        db, user, pagination, kind.value if kind else None, owner_id, verification_status, doc_status
    )


@router.post("/{document_id}/complete", response_model=s.Document)
async def complete(db: DB, user: CurrentUser, storage: StorageDep, document_id: uuid.UUID):
    return await service.complete_upload(db, storage, user, document_id)


@router.get("/{document_id}/download-url", response_model=s.DownloadUrl)
async def download_url(db: DB, user: CurrentUser, storage: StorageDep, document_id: uuid.UUID):
    return await service.download_url(db, storage, user, document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(db: DB, user: CurrentUser, storage: StorageDep, document_id: uuid.UUID):
    await service.delete_document(db, storage, user, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{document_id}/verification", response_model=s.Document)
async def verify(db: DB, admin: AdminUser, document_id: uuid.UUID, body: s.VerificationRequest):
    return await service.set_verification(db, admin, document_id, body)
