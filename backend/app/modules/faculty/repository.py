import uuid
from typing import Any

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.faculty.models import Faculty
from app.modules.users.models import User


async def get(session: AsyncSession, user_id: uuid.UUID) -> Faculty | None:
    return (await session.execute(select(Faculty).where(Faculty.user_id == user_id))).scalar_one_or_none()


def list_query(q: str | None) -> Select[Any]:
    stmt = select(Faculty, User).join(User, User.id == Faculty.user_id)
    if q:
        escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(like, escape="\\"),
                User.email.ilike(like, escape="\\"),
                Faculty.department.ilike(like, escape="\\"),
            )
        )
    return stmt.order_by(User.full_name, Faculty.user_id)
