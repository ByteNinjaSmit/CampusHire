from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.core.pagination import PageParams, make_page, paginate
from app.core.side_effects import audit
from app.modules.faculty import repository as repo
from app.modules.faculty import schemas as s
from app.modules.users.models import User


def _snap(f: Any) -> dict[str, Any]:
    return {"department": f.department, "designation": f.designation, "employee_id": f.employee_id}


async def list_faculty(session: AsyncSession, params: PageParams, q: str | None) -> dict[str, Any]:
    rows, total = await paginate(session, repo.list_query(q), params, scalars=False)
    items = [
        s.FacultyListItem(
            user_id=f.user_id,
            department=f.department,
            designation=f.designation,
            employee_id=f.employee_id,
            full_name=u.full_name,
            email=u.email,
            is_active=u.is_active,
        )
        for f, u in rows
    ]
    return make_page(items, total, params)


async def get_me(session: AsyncSession, user: User) -> s.FacultyProfile:
    faculty = await repo.get(session, user.id)
    if faculty is None:
        raise not_found("Faculty profile not found")
    return s.FacultyProfile.model_validate(faculty)


async def update_me(session: AsyncSession, user: User, data: s.FacultyProfileUpdate) -> s.FacultyProfile:
    faculty = await repo.get(session, user.id)
    if faculty is None:
        raise not_found("Faculty profile not found")
    before = _snap(faculty)
    for field in data.model_fields_set:
        value = getattr(data, field)
        if field == "department" and value is None:
            continue  # NOT NULL
        setattr(faculty, field, value)
    await session.flush()  # uq_faculty_employee_id -> 409 CONFLICT
    audit(session, user, "faculty.update_profile", "faculty", faculty.user_id, before=before, after=_snap(faculty))
    return s.FacultyProfile.model_validate(faculty)
