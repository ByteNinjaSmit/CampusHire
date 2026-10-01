"""Report / job schemas. Shapes mirror plan section 6.9 and 6.11 exactly (snake_case, numbers not strings)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_serializer

Number = int | float
CellValue = str | int | float | None

KpiFormat = Literal["number", "percent", "currency", "text"]
ColumnFormat = Literal["number", "percent", "currency", "date", "datetime", "text"]


class ReportMeta(BaseModel):
    key: str
    title: str
    description: str
    formats: list[Literal["pdf", "xlsx"]]
    params: list[Literal["from", "to", "internship_id", "company_id", "student_id"]]


class _DropNone(BaseModel):
    """Optional keys (`delta?`, `hint?`, `format?`) are omitted from JSON instead of being sent as null."""

    @model_serializer(mode="wrap")
    def _omit_none(self, handler):  # type: ignore[no-untyped-def]
        return {k: v for k, v in handler(self).items() if v is not None}


class Kpi(_DropNone):
    label: str
    value: Number | str
    format: KpiFormat | None = "number"
    delta: float | None = None
    hint: str | None = None


class Series(BaseModel):
    name: str
    data: list[Number]


class NameValue(BaseModel):
    name: str
    value: Number


class Indicator(BaseModel):
    name: str
    max: Number


class XYChart(BaseModel):
    id: str
    type: Literal["line", "bar", "area"]
    title: str
    x: list[str]
    series: list[Series]


class PieChart(BaseModel):
    id: str
    type: Literal["pie", "donut"]
    title: str
    data: list[NameValue]


class RadarChart(BaseModel):
    id: str
    type: Literal["radar"]
    title: str
    indicators: list[Indicator]
    series: list[Series]


ReportChart = Annotated[XYChart | PieChart | RadarChart, Field(discriminator="type")]


class Column(_DropNone):
    key: str
    label: str
    format: ColumnFormat | None = None


class ReportTable(BaseModel):
    id: str
    title: str
    columns: list[Column]
    rows: list[dict[str, CellValue]]


class ReportData(BaseModel):
    key: str
    title: str
    generated_at: datetime
    params: dict[str, Any] = Field(default_factory=dict)
    kpis: list[Kpi] = Field(default_factory=list)
    charts: list[ReportChart] = Field(default_factory=list)
    tables: list[ReportTable] = Field(default_factory=list)


class ExportParams(BaseModel):
    """Report parameters; ``from`` is exposed as ``from`` on the wire (alias)."""

    model_config = {"populate_by_name": True}

    from_: date | None = Field(default=None, alias="from")
    to: date | None = None
    internship_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    student_id: uuid.UUID | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.from_:
            out["from"] = self.from_.isoformat()
        if self.to:
            out["to"] = self.to.isoformat()
        for k in ("internship_id", "company_id", "student_id"):
            v = getattr(self, k)
            if v is not None:
                out[k] = str(v)
        return out


class ExportRequest(BaseModel):
    format: Literal["pdf", "xlsx"]
    params: ExportParams = Field(default_factory=lambda: ExportParams())


class JobOut(BaseModel):
    id: uuid.UUID
    type: Literal["REPORT_EXPORT", "DATA_EXPORT", "DATA_IMPORT", "COMPLIANCE_SCAN"]
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED"]
    progress: int
    params: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    download_url: str | None
    created_at: datetime
    finished_at: datetime | None
