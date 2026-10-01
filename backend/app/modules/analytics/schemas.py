"""Analytics schemas: ``DashboardData`` (plan 6.11). KPI / chart models are shared with reports."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.reports.schemas import Kpi, ReportChart


class DashboardItem(BaseModel):
    id: uuid.UUID
    title: str
    subtitle: str | None = None
    status: str | None = None
    at: datetime | None = None
    link: str


class DashboardList(BaseModel):
    id: str
    title: str
    items: list[DashboardItem] = Field(default_factory=list)


class DashboardData(BaseModel):
    role: Literal["ADMIN", "FACULTY", "STUDENT", "COMPANY"]
    kpis: list[Kpi] = Field(default_factory=list)
    charts: list[ReportChart] = Field(default_factory=list)
    lists: list[DashboardList] = Field(default_factory=list)
