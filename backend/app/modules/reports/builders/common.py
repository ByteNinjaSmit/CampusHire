"""Shared helpers for report builders: parameter parsing, role scoping, bucketing, chart/table constructors."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base import utcnow
from app.core.errors import AppError, unprocessable
from app.core.permissions import member_company_id, owned_internships_clause
from app.modules.internships.models import Internship
from app.modules.reports.schemas import (
    Column,
    Indicator,
    Kpi,
    NameValue,
    PieChart,
    RadarChart,
    ReportTable,
    Series,
    XYChart,
)
from app.modules.users.models import User

APPLICATION_STATUSES = ["PENDING", "UNDER_REVIEW", "SHORTLISTED", "INTERVIEW", "ACCEPTED", "REJECTED", "WITHDRAWN"]
OPEN_STATUSES = ("PENDING", "UNDER_REVIEW", "SHORTLISTED", "INTERVIEW")
TABLE_ROW_CAP = 500


# --------------------------------------------------------------------------- params
@dataclass
class Filters:
    date_from: datetime | None = None  # inclusive, UTC midnight
    date_to: datetime | None = None  # exclusive (day after ``to``)
    internship_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    student_id: uuid.UUID | None = None
    raw_from: date | None = None
    raw_to: date | None = None

    def apply(self, column: Any) -> list[Any]:
        """Clauses restricting a datetime ``column`` to the requested period."""
        out = []
        if self.date_from is not None:
            out.append(column >= self.date_from)
        if self.date_to is not None:
            out.append(column < self.date_to)
        return out

    def params_out(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.raw_from:
            out["from"] = self.raw_from.isoformat()
        if self.raw_to:
            out["to"] = self.raw_to.isoformat()
        for k in ("internship_id", "company_id", "student_id"):
            v = getattr(self, k)
            if v is not None:
                out[k] = str(v)
        return out


def _as_date(v: Any, name: str) -> date | None:
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError as exc:
        raise unprocessable(f"Invalid {name}", details=[{"field": name, "message": "Expected YYYY-MM-DD"}]) from exc


def _as_uuid(v: Any, name: str) -> uuid.UUID | None:
    if v in (None, ""):
        return None
    if isinstance(v, uuid.UUID):
        return v
    try:
        return uuid.UUID(str(v))
    except ValueError as exc:
        raise unprocessable(f"Invalid {name}", details=[{"field": name, "message": "Expected a UUID"}]) from exc


def parse_params(params: dict[str, Any] | None) -> Filters:
    p = params or {}
    d_from = _as_date(p.get("from", p.get("from_")), "from")
    d_to = _as_date(p.get("to"), "to")
    if d_from and d_to and d_from > d_to:
        raise unprocessable("from must not be after to", details=[{"field": "from", "message": "after to"}])
    return Filters(
        date_from=datetime(d_from.year, d_from.month, d_from.day, tzinfo=UTC) if d_from else None,
        date_to=(datetime(d_to.year, d_to.month, d_to.day, tzinfo=UTC) + timedelta(days=1)) if d_to else None,
        internship_id=_as_uuid(p.get("internship_id"), "internship_id"),
        company_id=_as_uuid(p.get("company_id"), "company_id"),
        student_id=_as_uuid(p.get("student_id"), "student_id"),
        raw_from=d_from,
        raw_to=d_to,
    )


async def internship_scope(session: AsyncSession, user: User, f: Filters) -> list[Any]:
    """Clauses over ``Internship`` for staff reports: ownership scope (ADMIN = all) + optional filters."""
    company_id = await member_company_id(session, user)
    clauses = [owned_internships_clause(user, company_id)]
    clauses.extend(internship_filters(f))
    return clauses


def internship_filters(f: Filters) -> list[Any]:
    clauses = []
    if f.internship_id:
        clauses.append(Internship.id == f.internship_id)
    if f.company_id:
        clauses.append(Internship.company_id == f.company_id)
    return clauses


def student_target(user: User, f: Filters) -> uuid.UUID:
    """Student reports: a student sees only themselves; ADMIN must pass ``student_id``."""
    if user.role == "STUDENT":
        return user.id
    if f.student_id is None:
        raise AppError(
            422, "VALIDATION_ERROR", "student_id is required", [{"field": "student_id", "message": "Required"}]
        )
    return f.student_id


# --------------------------------------------------------------------------- numbers
def num(v: Any, digits: int = 2) -> int | float:
    if v is None:
        return 0
    if isinstance(v, Decimal):
        v = float(v)
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    return round(float(v), digits)


def pct(n: float, d: float) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def iso(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=UTC)
        return v.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


def trunc(unit: str, column: Any) -> Any:
    """``date_trunc(unit, column AT TIME ZONE 'UTC')`` -> naive UTC timestamp."""
    return func.date_trunc(unit, func.timezone("UTC", column))


def day_range(start: date, end: date) -> list[date]:
    n = (end - start).days
    return [start + timedelta(days=i) for i in range(max(n, 0) + 1)]


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_range(start: date, end: date) -> list[date]:
    out, cur = [], week_start(start)
    last = week_start(end)
    while cur <= last:
        out.append(cur)
        cur += timedelta(days=7)
    return out


def month_key(d: datetime | date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def month_range(start: date, end: date) -> list[str]:
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def to_date(v: Any) -> date:
    return v.date() if isinstance(v, datetime) else v


# --------------------------------------------------------------------------- constructors
def kpi(label: str, value: Any, fmt: str = "number", hint: str | None = None, delta: float | None = None) -> Kpi:
    if not isinstance(value, str):
        value = num(value, 1 if fmt == "percent" else 2)
    return Kpi(label=label, value=value, format=fmt, hint=hint, delta=delta)  # type: ignore[arg-type]


def xy_chart(
    id: str,  # noqa: A002
    type: str,  # noqa: A002
    title: str,
    x: Sequence[str],
    series: Iterable[tuple[str, Sequence[Any]]],
) -> XYChart:
    return XYChart(
        id=id,
        type=type,  # type: ignore[arg-type]
        title=title,
        x=[str(v) for v in x],
        series=[Series(name=n, data=[num(v) for v in d]) for n, d in series],
    )


def pie_chart(id: str, type: str, title: str, data: Iterable[tuple[str, Any]]) -> PieChart:  # noqa: A002
    return PieChart(
        id=id,
        type=type,  # type: ignore[arg-type]
        title=title,
        data=[NameValue(name=str(n), value=num(v)) for n, v in data],
    )


def radar_chart(
    id: str,  # noqa: A002
    title: str,
    indicators: Iterable[tuple[str, Any]],
    series: Iterable[tuple[str, Sequence[Any]]],
) -> RadarChart:
    return RadarChart(
        id=id,
        type="radar",
        title=title,
        indicators=[Indicator(name=n, max=num(m)) for n, m in indicators],
        series=[Series(name=n, data=[num(v) for v in d]) for n, d in series],
    )


def table(
    id: str,  # noqa: A002
    title: str,
    columns: Sequence[tuple[str, ...]],
    rows: Iterable[dict[str, Any]],
) -> ReportTable:
    cols = [Column(key=c[0], label=c[1], format=(c[2] if len(c) > 2 else None)) for c in columns]  # type: ignore[arg-type]
    keys = [c.key for c in cols]
    clean: list[dict[str, Any]] = []
    for r in rows:
        out: dict[str, Any] = {}
        for k in keys:
            v = r.get(k)
            if isinstance(v, (datetime, date)):
                v = iso(v)
            elif isinstance(v, Decimal):
                v = float(v)
            elif isinstance(v, bool):
                v = "Yes" if v else "No"
            elif isinstance(v, uuid.UUID):
                v = str(v)
            elif v is not None and not isinstance(v, (str, int, float)):
                v = str(v)
            out[k] = v
        clean.append(out)
    return ReportTable(id=id, title=title, columns=cols, rows=clean)


def now_utc() -> datetime:
    return utcnow()
