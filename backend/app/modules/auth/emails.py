"""Verification / password reset e-mails. Rendered by the worker (WP4) from templates verify_email / reset_password."""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.side_effects import queue_email
from app.modules.auth import repository as repo
from app.modules.users.models import User


async def send_verification_email(session: AsyncSession, user: User) -> None:
    raw = await repo.issue_user_token(
        session, user.id, "VERIFY_EMAIL", timedelta(hours=settings.VERIFY_TOKEN_TTL_HOURS)
    )
    queue_email(
        session,
        "verify_email",
        user.email,
        {
            "full_name": user.full_name,
            "verify_url": f"{settings.FRONTEND_URL}/verify-email?token={raw}",
            "expires_hours": settings.VERIFY_TOKEN_TTL_HOURS,
        },
    )


async def send_reset_email(session: AsyncSession, user: User) -> None:
    raw = await repo.issue_user_token(
        session, user.id, "RESET_PASSWORD", timedelta(hours=settings.RESET_TOKEN_TTL_HOURS)
    )
    queue_email(
        session,
        "reset_password",
        user.email,
        {
            "full_name": user.full_name,
            "reset_url": f"{settings.FRONTEND_URL}/reset-password?token={raw}",
            "expires_hours": settings.RESET_TOKEN_TTL_HOURS,
        },
    )
