"""Document schemas (plan 6.9)."""

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.core.types import DocumentKind
from app.modules.users.schemas import DocumentSummary

__all__ = [
    "Document",
    "DocumentOwner",
    "DocumentSummary",
    "DownloadUrl",
    "UploadTarget",
    "UploadTicket",
    "UploadUrlRequest",
    "VerificationRequest",
]


class UploadUrlRequest(BaseModel):
    kind: DocumentKind
    filename: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    content_type: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    size_bytes: Annotated[int, Field(gt=0)]


class UploadTarget(BaseModel):
    url: str
    fields: dict[str, Any]


class UploadTicket(BaseModel):
    document_id: uuid.UUID
    upload: UploadTarget
    expires_in: int
    max_bytes: int


class DocumentOwner(BaseModel):
    id: uuid.UUID
    full_name: str


class Document(DocumentSummary):
    owner: DocumentOwner
    verification_note: str | None = None
    verified_at: datetime | None = None
    in_use: bool = False


class VerificationRequest(BaseModel):
    verification_status: Literal["PENDING", "VERIFIED", "REJECTED"]
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None = None


class DownloadUrl(BaseModel):
    url: str
    expires_in: int
