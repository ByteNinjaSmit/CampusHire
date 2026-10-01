"""PDF renderer (ReportLab only, no system libraries): title page, KPI table, charts as ReportLab drawings, tables."""

from __future__ import annotations

import io
import logging
from typing import Any
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.spider import SpiderChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.modules.reports.renderers.common import fmt_value
from app.modules.reports.schemas import PieChart, RadarChart, ReportData, ReportTable, XYChart

log = logging.getLogger(__name__)

INDIGO = colors.HexColor("#4F46E5")
INDIGO_DARK = colors.HexColor("#312E81")
SLATE = colors.HexColor("#475569")
LIGHT = colors.HexColor("#F4F4F5")
PALETTE = [colors.HexColor(c) for c in ("#6366F1", "#22C55E", "#F59E0B", "#06B6D4", "#EC4899", "#8B5CF6", "#64748B")]
MAX_CELL_CHARS = 110
MAX_BAR_CATEGORIES = 12


def _clean(value: Any, limit: int = MAX_CELL_CHARS) -> str:
    """Escape for Paragraph markup and keep to the Latin-1 range the built-in PDF fonts can draw."""
    text = str(value)
    text = text.encode("cp1252", "replace").decode("cp1252")
    if len(text) > limit:
        text = text[: limit - 1] + "..."
    return escape(text)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle("brand", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=14, textColor=colors.white),
        "cover_title": ParagraphStyle(
            "cover_title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=30, leading=36,
            textColor=INDIGO_DARK, alignment=0, spaceAfter=10,
        ),
        "meta": ParagraphStyle("meta", parent=base["Normal"], fontSize=10.5, leading=15, textColor=SLATE),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=14, textColor=INDIGO_DARK,
            spaceBefore=12, spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=11, textColor=INDIGO_DARK,
            spaceBefore=8, spaceAfter=4,
        ),
        "kpi_label": ParagraphStyle("kpi_label", parent=base["Normal"], fontSize=8.5, leading=11, textColor=SLATE),
        "kpi_value": ParagraphStyle(
            "kpi_value", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=INDIGO_DARK
        ),
        "kpi_hint": ParagraphStyle("kpi_hint", parent=base["Normal"], fontSize=7, leading=9, textColor=colors.HexColor("#71717A")),
        "cell": ParagraphStyle("cell", parent=base["Normal"], fontSize=7.5, leading=9.5),
        "cell_head": ParagraphStyle(
            "cell_head", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=9.5, textColor=colors.white
        ),
        "muted": ParagraphStyle("muted", parent=base["Normal"], fontSize=9, textColor=colors.HexColor("#71717A")),
    }


# --------------------------------------------------------------------------- charts
def _short(label: str, n: int = 16) -> str:
    label = label.encode("cp1252", "replace").decode("cp1252")
    return label if len(label) <= n else label[: n - 1] + "."


def _legend(drawing: Drawing, names: list[str], x: float, y: float) -> None:
    lg = Legend()
    lg.x, lg.y = x, y
    lg.fontName, lg.fontSize = "Helvetica", 7.5
    lg.alignment = "right"
    lg.dx = lg.dy = 7
    lg.deltay = 11
    lg.colorNamePairs = [(PALETTE[i % len(PALETTE)], _short(n, 28)) for i, n in enumerate(names)]
    drawing.add(lg)


def _xy_drawing(chart: XYChart, width: float) -> Drawing | None:
    if not chart.x or not chart.series:
        return None
    is_bar = chart.type == "bar"
    x_labels, series = list(chart.x), [list(s.data) for s in chart.series]
    if is_bar and len(x_labels) > MAX_BAR_CATEGORIES:
        x_labels = x_labels[:MAX_BAR_CATEGORIES]
        series = [s[:MAX_BAR_CATEGORIES] for s in series]
    legend_w = 120 if len(chart.series) > 1 else 0
    d = Drawing(width, 190)
    c: Any = VerticalBarChart() if is_bar else HorizontalLineChart()
    c.x, c.y = 38, 42
    c.width, c.height = width - 50 - legend_w, 120
    c.data = series
    c.valueAxis.valueMin = 0
    top = max((max(s) for s in series if s), default=0)
    if top <= 0:
        c.valueAxis.valueMax = 1
    c.valueAxis.labels.fontSize = 7
    c.categoryAxis.labels.fontSize = 6.5
    n = len(x_labels)
    if is_bar:
        c.categoryAxis.categoryNames = [_short(x, 14) for x in x_labels]
        c.bars.strokeColor = None
        for i in range(len(series)):
            c.bars[i].fillColor = PALETTE[i % len(PALETTE)]
        c.groupSpacing = 8
    else:
        step = max(1, n // 10)
        c.categoryAxis.categoryNames = [_short(x, 10) if i % step == 0 else "" for i, x in enumerate(x_labels)]
        for i in range(len(series)):
            c.lines[i].strokeColor = PALETTE[i % len(PALETTE)]
            c.lines[i].strokeWidth = 1.6
            c.lines[i].symbol = None
    if n > 6 or any(len(x) > 8 for x in x_labels):
        c.categoryAxis.labels.angle = 35
        c.categoryAxis.labels.boxAnchor = "ne"
        c.categoryAxis.labels.dy = -2
    d.add(c)
    if legend_w:
        _legend(d, [s.name for s in chart.series], width - legend_w + 10, 150)
    return d


def _pie_drawing(chart: PieChart, width: float) -> Drawing | None:
    data = [(p.name, float(p.value)) for p in chart.data if p.value and float(p.value) > 0]
    if not data:
        return None
    d = Drawing(width, 170)
    pie = Pie()
    pie.x, pie.y, pie.width, pie.height = 40, 15, 140, 140
    pie.data = [v for _, v in data]
    pie.labels = [f"{v:g}" for _, v in data]
    pie.sideLabels = False
    pie.simpleLabels = 1
    pie.slices.strokeColor = colors.white
    pie.slices.strokeWidth = 1
    pie.slices.fontSize = 7
    for i in range(len(data)):
        pie.slices[i].fillColor = PALETTE[i % len(PALETTE)]
    if chart.type == "donut" and hasattr(pie, "innerRadiusFraction"):
        pie.innerRadiusFraction = 0.55
    d.add(pie)
    _legend(d, [f"{n} ({v:g})" for n, v in data], 230, 140)
    return d


def _radar_drawing(chart: RadarChart, width: float) -> Drawing | None:
    if not chart.indicators or not chart.series:
        return None
    d = Drawing(width, 220)
    sp = SpiderChart()
    sp.x, sp.y, sp.width, sp.height = 70, 25, 170, 170
    maxes = [float(i.max) or 1.0 for i in chart.indicators]
    sp.data = [
        [min(100.0, 100.0 * float(v) / maxes[i]) for i, v in enumerate(s.data[: len(maxes)])] for s in chart.series
    ]
    sp.labels = [_short(i.name, 18) for i in chart.indicators]
    sp.strands.strokeWidth = 1.4
    for i in range(len(chart.series)):
        sp.strands[i].strokeColor = PALETTE[i % len(PALETTE)]
        sp.strands[i].fillColor = None
    sp.labels and setattr(sp, "labelRadius", 1.15)
    d.add(sp)
    d.add(String(70, 5, "Values scaled to each indicator maximum", fontName="Helvetica", fontSize=6.5, fillColor=SLATE))
    _legend(d, [s.name for s in chart.series], 290, 180)
    return d


def _chart_fallback(chart: Any, styles: dict[str, ParagraphStyle]) -> Table:
    rows: list[list[Any]] = []
    if isinstance(chart, XYChart):
        rows.append([Paragraph("", styles["cell_head"])] + [Paragraph(_clean(s.name), styles["cell_head"]) for s in chart.series])
        for i, x in enumerate(chart.x[:30]):
            rows.append([Paragraph(_clean(x), styles["cell"])] + [Paragraph(fmt_value(s.data[i], None), styles["cell"]) for s in chart.series])
    elif isinstance(chart, PieChart):
        rows.append([Paragraph("Name", styles["cell_head"]), Paragraph("Value", styles["cell_head"])])
        for p in chart.data:
            rows.append([Paragraph(_clean(p.name), styles["cell"]), Paragraph(fmt_value(p.value, None), styles["cell"])])
    else:
        rows.append([Paragraph("Indicator", styles["cell_head"])] + [Paragraph(_clean(s.name), styles["cell_head"]) for s in chart.series])
        for i, ind in enumerate(chart.indicators):
            rows.append([Paragraph(_clean(ind.name), styles["cell"])] + [Paragraph(fmt_value(s.data[i], None), styles["cell"]) for s in chart.series])
    t = Table(rows, hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), INDIGO), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D4D4D8"))]))
    return t


def _chart_flowables(chart: Any, width: float, styles: dict[str, ParagraphStyle]) -> list[Any]:
    title = Paragraph(_clean(chart.title, 120), styles["h3"])
    drawing: Drawing | None = None
    try:
        if isinstance(chart, XYChart):
            drawing = _xy_drawing(chart, width)
        elif isinstance(chart, PieChart):
            drawing = _pie_drawing(chart, width)
        else:
            drawing = _radar_drawing(chart, width)
    except Exception:  # noqa: BLE001 - never fail an export over one chart; fall back to its data
        log.exception("chart %s failed to render, falling back to a table", getattr(chart, "id", "?"))
        return [KeepTogether([title, _chart_fallback(chart, styles)]), Spacer(1, 6)]
    if drawing is None:
        return [KeepTogether([title, Paragraph("No data for this period.", styles["muted"])]), Spacer(1, 6)]
    return [KeepTogether([title, drawing]), Spacer(1, 6)]


# --------------------------------------------------------------------------- tables
def _col_widths(t: ReportTable, avail: float) -> list[float]:
    weights = []
    for col in t.columns:
        longest = max([len(col.label)] + [len(fmt_value(r.get(col.key), col.format)) for r in t.rows[:60]])
        weights.append(max(6, min(longest, 40)))
    total = sum(weights) or 1
    return [avail * w / total for w in weights]


def _table_flowables(t: ReportTable, avail: float, styles: dict[str, ParagraphStyle]) -> list[Any]:
    out: list[Any] = [Paragraph(_clean(t.title, 120), styles["h2"])]
    if not t.rows:
        out.append(Paragraph("No records.", styles["muted"]))
        return out
    data: list[list[Any]] = [[Paragraph(_clean(c.label, 40), styles["cell_head"]) for c in t.columns]]
    for r in t.rows:
        data.append([Paragraph(_clean(fmt_value(r.get(c.key), c.format)), styles["cell"]) for c in t.columns])
    tbl = Table(data, colWidths=_col_widths(t, avail), repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INDIGO),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D4D4D8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    out.append(tbl)
    return out


def _kpi_table(report: ReportData, avail: float, styles: dict[str, ParagraphStyle]) -> Table | None:
    if not report.kpis:
        return None
    per_row = 3
    cells: list[Any] = []
    for k in report.kpis:
        inner = [
            Paragraph(_clean(k.label, 60), styles["kpi_label"]),
            Paragraph(_clean(fmt_value(k.value, k.format), 40), styles["kpi_value"]),
        ]
        if k.hint:
            inner.append(Paragraph(_clean(k.hint, 90), styles["kpi_hint"]))
        cells.append(inner)
    while len(cells) % per_row:
        cells.append("")
    rows = [cells[i : i + per_row] for i in range(0, len(cells), per_row)]
    t = Table(rows, colWidths=[avail / per_row] * per_row)
    t.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D4D4D8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D4D4D8")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


# --------------------------------------------------------------------------- entry point
def render_pdf(report: ReportData, generated_for: str | None = None) -> bytes:
    styles = _styles()
    widest = max((len(t.columns) for t in report.tables), default=0)
    page = landscape(A4) if widest > 6 else A4
    margin = 15 * mm
    avail = page[0] - 2 * margin
    buf = io.BytesIO()
    title = report.title
    doc = SimpleDocTemplate(
        buf, pagesize=page, leftMargin=margin, rightMargin=margin, topMargin=18 * mm, bottomMargin=16 * mm,
        title=title, author="CampusHire", subject="CampusHire report",
    )

    story: list[Any] = []
    # ---- title page
    band = Table([[Paragraph("CampusHire", styles["brand"])]], colWidths=[avail], rowHeights=[16 * mm])
    band.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), INDIGO), ("LEFTPADDING", (0, 0), (-1, -1), 12), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [band, Spacer(1, 55 * mm), Paragraph(_clean(title, 80), styles["cover_title"])]
    story.append(Paragraph("College internship and talent management report", styles["meta"]))
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(f"<b>Generated:</b> {report.generated_at.strftime('%Y-%m-%d %H:%M')} UTC", styles["meta"]))
    if generated_for:
        story.append(Paragraph(f"<b>Prepared for:</b> {_clean(generated_for, 80)}", styles["meta"]))
    for k, v in report.params.items():
        story.append(Paragraph(f"<b>{_clean(str(k).replace('_', ' ').title(), 40)}:</b> {_clean(v, 80)}", styles["meta"]))
    story.append(PageBreak())

    # ---- KPIs
    kt = _kpi_table(report, avail, styles)
    if kt is not None:
        story += [Paragraph("Key metrics", styles["h2"]), kt, Spacer(1, 6)]

    # ---- charts
    if report.charts:
        story.append(Paragraph("Charts", styles["h2"]))
        for chart in report.charts:
            story += _chart_flowables(chart, min(avail, 175 * mm), styles)

    # ---- tables
    for t in report.tables:
        story += _table_flowables(t, avail, styles)

    def _footer(canvas: Any, d: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(SLATE)
        canvas.drawString(margin, 9 * mm, f"CampusHire - {_clean(title, 60)}")
        canvas.drawRightString(page[0] - margin, 9 * mm, f"Page {d.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=_footer)
    return buf.getvalue()
