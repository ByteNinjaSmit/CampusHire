"""MinIO / S3 access (boto3).

Two clients (plan 1.3): ``s3_internal`` (endpoint reachable from API/workers) does put/head/get/delete;
``s3_public`` (endpoint reachable from the browser, e.g. http://localhost:9000) is used ONLY to presign,
because the signature covers the Host header.

The ``Storage`` facade exposes async methods (boto3 is blocking, so calls run in a worker thread).
Inject it with ``Depends(get_storage)`` so tests can override it with an in-memory fake.
"""

import logging
from typing import Any

import anyio
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.types import MAX_RESUME_BYTES

log = logging.getLogger(__name__)

UPLOAD_TTL_SECONDS = 600  # presigned POST
DOWNLOAD_TTL_SECONDS = 300  # presigned GET

_cfg = Config(signature_version="s3v4", s3={"addressing_style": "path"}, retries={"max_attempts": 2})
_internal: Any = None
_public: Any = None


def s3_internal() -> Any:
    global _internal
    if _internal is None:
        _internal = boto3.client(
            "s3",
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            region_name=settings.MINIO_REGION,
            config=_cfg,
        )
    return _internal


def s3_public() -> Any:
    global _public
    if _public is None:
        _public = boto3.client(
            "s3",
            endpoint_url=settings.MINIO_PUBLIC_URL,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            region_name=settings.MINIO_REGION,
            config=_cfg,
        )
    return _public


def ensure_buckets() -> None:
    """Create the configured buckets if missing (sync; used by the container entrypoint and the seed)."""
    client = s3_internal()
    for bucket in settings.buckets:
        try:
            client.head_bucket(Bucket=bucket)
        except ClientError:
            client.create_bucket(Bucket=bucket)
            log.info("created bucket %s", bucket)


class Storage:
    # ---- sync primitives ------------------------------------------------------------------------
    def _presign_post(
        self, bucket: str, key: str, content_type: str, max_bytes: int, expires: int
    ) -> dict[str, Any]:
        return s3_public().generate_presigned_post(
            Bucket=bucket,
            Key=key,
            Fields={"Content-Type": content_type},
            Conditions=[
                ["content-length-range", 1, max_bytes],
                {"Content-Type": content_type},
            ],
            ExpiresIn=expires,
        )

    def _presign_get(self, bucket: str, key: str, expires: int, filename: str | None) -> str:
        params: dict[str, Any] = {"Bucket": bucket, "Key": key}
        if filename:
            safe = filename.replace('"', "")
            params["ResponseContentDisposition"] = f'inline; filename="{safe}"'
        return s3_public().generate_presigned_url("get_object", Params=params, ExpiresIn=expires)

    def _head(self, bucket: str, key: str) -> dict[str, Any] | None:
        try:
            r = s3_internal().head_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return None
            raise
        return {"size": int(r["ContentLength"]), "content_type": r.get("ContentType")}

    def _read_range(self, bucket: str, key: str, start: int, end: int) -> bytes:
        r = s3_internal().get_object(Bucket=bucket, Key=key, Range=f"bytes={start}-{end}")
        return r["Body"].read()

    def _get(self, bucket: str, key: str) -> bytes:
        return s3_internal().get_object(Bucket=bucket, Key=key)["Body"].read()

    def _delete(self, bucket: str, key: str) -> None:
        s3_internal().delete_object(Bucket=bucket, Key=key)

    def _put(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        s3_internal().put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)

    # ---- async API ------------------------------------------------------------------------------
    async def presign_post(
        self,
        bucket: str,
        key: str,
        content_type: str,
        max_bytes: int = MAX_RESUME_BYTES,
        expires: int = UPLOAD_TTL_SECONDS,
    ) -> dict[str, Any]:
        """Return ``{"url": ..., "fields": {...}}`` for a browser multipart POST (offline signing, no I/O)."""
        return self._presign_post(bucket, key, content_type, max_bytes, expires)

    async def presign_get(
        self, bucket: str, key: str, filename: str | None = None, expires: int = DOWNLOAD_TTL_SECONDS
    ) -> str:
        return self._presign_get(bucket, key, expires, filename)

    async def head(self, bucket: str, key: str) -> dict[str, Any] | None:
        """``{"size": int, "content_type": str}`` or None when the object does not exist."""
        return await anyio.to_thread.run_sync(self._head, bucket, key)

    async def read_range(self, bucket: str, key: str, start: int = 0, end: int = 4) -> bytes:
        return await anyio.to_thread.run_sync(self._read_range, bucket, key, start, end)

    async def get_object(self, bucket: str, key: str) -> bytes:
        return await anyio.to_thread.run_sync(self._get, bucket, key)

    async def delete(self, bucket: str, key: str) -> None:
        await anyio.to_thread.run_sync(self._delete, bucket, key)

    async def put_object(
        self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        await anyio.to_thread.run_sync(self._put, bucket, key, data, content_type)


storage = Storage()


def get_storage() -> Storage:
    """FastAPI dependency. Tests override this with FakeStorage."""
    return storage
