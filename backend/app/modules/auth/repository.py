import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import utcnow
from app.core.security import generate_token, hash_token
from app.modules.admin.models import LoginEvent
from app.modules.auth.models import RefreshToken, UserToken


# ---- refresh tokens ---------------------------------------------------------------------------------
async def get_refresh_by_hash(session: AsyncSession, token_hash: str) -> RefreshToken | None:
    return (
        await session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update())
    ).scalar_one_or_none()


def new_refresh_token(
    user_id: uuid.UUID,
    family_id: uuid.UUID,
    ttl_days: int,
    ip: str | None,
    user_agent: str | None,
) -> tuple[RefreshToken, str]:
    raw = generate_token()
    row = RefreshToken(
        id=uuid.uuid4(),
        user_id=user_id,
        family_id=family_id,
        token_hash=hash_token(raw),
        expires_at=utcnow() + timedelta(days=ttl_days),
        ip=ip,
        user_agent=user_agent,
    )
    return row, raw


async def revoke_family(session: AsyncSession, family_id: uuid.UUID) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


async def revoke_user_tokens(session: AsyncSession, user_id: uuid.UUID, except_family: uuid.UUID | None = None) -> None:
    stmt = update(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
    if except_family is not None:
        stmt = stmt.where(RefreshToken.family_id != except_family)
    await session.execute(stmt.values(revoked_at=utcnow()))


# ---- user tokens (verify email / reset password) -------------------------------------------------------
async def issue_user_token(session: AsyncSession, user_id: uuid.UUID, purpose: str, ttl: timedelta) -> str:
    """Create a single-use token; any older unused tokens for the same purpose are invalidated."""
    await session.execute(
        update(UserToken)
        .where(UserToken.user_id == user_id, UserToken.purpose == purpose, UserToken.used_at.is_(None))
        .values(used_at=utcnow())
    )
    raw = generate_token()
    session.add(
        UserToken(
            id=uuid.uuid4(),
            user_id=user_id,
            purpose=purpose,
            token_hash=hash_token(raw),
            expires_at=utcnow() + ttl,
        )
    )
    return raw


async def get_user_token(session: AsyncSession, raw: str, purpose: str) -> UserToken | None:
    return (
        await session.execute(
            select(UserToken)
            .where(UserToken.token_hash == hash_token(raw), UserToken.purpose == purpose)
            .with_for_update()
        )
    ).scalar_one_or_none()


def token_is_live(token: UserToken, now: datetime | None = None) -> bool:
    return token.used_at is None and token.expires_at > (now or utcnow())


# ---- login events -------------------------------------------------------------------------------------
def add_login_event(
    session: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    email: str | None,
    success: bool,
    ip: str | None,
    user_agent: str | None,
) -> None:
    session.add(LoginEvent(user_id=user_id, email=email, success=success, ip=ip, user_agent=user_agent))
