"""Value formatting shared by the PDF and XLSX renderers."""

from __future__ import annotations

from datetime import datetime
from typing import Any

CURRENCY_SYMBOL = "INR "


def parse_iso(v: Any) -> datetime | None:
    if not isinstance(v, str):
        return None
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None


def fmt_number(v: float | int, digits: int | None = None) -> str:
    if isinstance(v, int) or float(v).is_integer():
        return f"{int(v):,}"
    return f"{v:,.{digits if digits is not None else 2}f}"


def fmt_value(value: Any, fmt: str | None) -> str:
    """Human readable string for a table cell / KPI value."""
    if value is None or value == "":
        return "-"
    if fmt == "percent" and isinstance(value, (int, float)):
        return f"{value:.1f}%"
    if fmt == "currency" and isinstance(value, (int, float)):
        return f"{CURRENCY_SYMBOL}{fmt_number(value, 0)}"
    if fmt in ("date", "datetime"):
        dt = parse_iso(value)
        if dt is not None:
            return dt.strftime("%Y-%m-%d" if fmt == "date" else "%Y-%m-%d %H:%M")
        return str(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return fmt_number(value)
    return str(value)


def safe_text(value: str) -> str:
    """Prefix formula-looking strings with an apostrophe so spreadsheets never evaluate them."""
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value
