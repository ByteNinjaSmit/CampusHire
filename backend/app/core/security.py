"""Argon2id hashing, JWT access tokens, opaque refresh/e-mail tokens, password policy."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings
from app.core.errors import AppError, unauthenticated
from app.core.validators import validate_password as password_policy  # noqa: F401  (re-exported)

# One module-level hasher: defaults are Argon2id (RFC 9106 low-memory profile).
_hasher = PasswordHasher()
# Used to burn comparable CPU time when the account does not exist (mitigates user enumeration by timing).
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def fake_verify(password: str) -> None:
    verify_password(_DUMMY_HASH, password)


# ---- access JWT -----------------------------------------------------------------------------------
def create_access_token(user_id: uuid.UUID | str, role: str, ttl_seconds: int | None = None) -> tuple[str, int]:
    ttl = settings.JWT_ACCESS_TTL_SECONDS if ttl_seconds is None else ttl_seconds
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "jti": uuid.uuid4().hex,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=ttl),
    }
    return jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM), ttl


def decode_access_token(token: str) -> dict[str, Any]:
    """Validate signature + exp + type. Raises AppError(401, TOKEN_EXPIRED | TOKEN_INVALID)."""
    try:
        claims = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise unauthenticated("Access token expired", "TOKEN_EXPIRED") from exc
    except jwt.InvalidTokenError as exc:
        raise unauthenticated("Invalid access token", "TOKEN_INVALID") from exc
    if claims.get("type") != "access":
        raise unauthenticated("Invalid access token", "TOKEN_INVALID")
    return claims


def try_decode_subject(token: str) -> str | None:
    """Best-effort ``sub`` extraction for rate limiting; never raises."""
    try:
        return str(decode_access_token(token)["sub"])
    except AppError:
        return None


# ---- opaque tokens (refresh, e-mail verification, password reset) -----------------------------------
def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
