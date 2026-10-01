"""Faculty schemas (plan 6.3)."""

from typing import Annotated

from pydantic import BaseModel, StringConstraints, field_validator

from app.modules.users.schemas import Department, FacultyProfile

EmployeeId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
Designation = Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)]


class FacultyListItem(FacultyProfile):
    full_name: str
    email: str
    is_active: bool = True


class FacultyProfileUpdate(BaseModel):
    department: Department | None = None
    designation: Designation | None = None
    employee_id: EmployeeId | None = None

    @field_validator("designation", "employee_id", mode="before")
    @classmethod
    def _blank_to_none(cls, v: object) -> object:
        return None if isinstance(v, str) and not v.strip() else v


__all__ = ["FacultyListItem", "FacultyProfile", "FacultyProfileUpdate"]
