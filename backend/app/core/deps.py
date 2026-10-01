"""FastAPI dependencies: current user, role guards, verified guard, pagination params, client info."""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.core.db import DB
from app.core.errors import AppError, forbidden, unauthenticated
from app.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, PageParams
from app.core.security import decode_access_token
from app.modules.users.models import User

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    db: DB,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials:
        raise unauthenticated()
    claims = decode_access_token(creds.credentials)
    try:
        user_id = uuid.UUID(claims["sub"])
    except (ValueError, KeyError) as exc:
        raise unauthenticated("Invalid access token", "TOKEN_INVALID") from exc
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise unauthenticated("Invalid access token", "TOKEN_INVALID")
    if not user.is_active:
        raise AppError(403, "ACCOUNT_DEACTIVATED", "This account has been deactivated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str) -> Callable[[User], Awaitable[User]]:
    """Dependency factory: 403 FORBIDDEN unless the authenticated user has one of ``roles``."""
    allowed = set(roles)

    async def _dep(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise forbidden()
        return user

    return _dep


async def require_verified(user: CurrentUser) -> User:
    if user.email_verified_at is None:
        raise AppError(403, "EMAIL_NOT_VERIFIED", "Please verify your email address first")
    return user


VerifiedUser = Annotated[User, Depends(require_verified)]
AdminUser = Annotated[User, Depends(require_roles("ADMIN"))]


def page_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


Pagination = Annotated[PageParams, Depends(page_params)]


@dataclass(frozen=True)
class ClientInfo:
    ip: str | None
    user_agent: str | None


def client_info(request: Request) -> ClientInfo:
    return ClientInfo(
        ip=request.client.host if request.client else None,
        user_agent=(request.headers.get("user-agent") or None) and request.headers["user-agent"][:500],
    )


Client = Annotated[ClientInfo, Depends(client_info)]
