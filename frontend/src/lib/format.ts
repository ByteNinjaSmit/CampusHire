import { format, formatDistanceToNowStrict, isValid, parseISO } from "date-fns";
import type { Kpi } from "@/lib/api/types";

const toDate = (v: string | Date | null | undefined): Date | null => {
  if (!v) return null;
  const d = typeof v === "string" ? parseISO(v) : v;
  return isValid(d) ? d : null;
};

export function formatDate(v: string | Date | null | undefined, pattern = "dd MMM yyyy"): string {
  const d = toDate(v);
  return d ? format(d, pattern) : "-";
}

export function formatDateTime(v: string | Date | null | undefined): string {
  const d = toDate(v);
  return d ? format(d, "dd MMM yyyy, h:mm a") : "-";
}

export function formatTime(v: string | Date | null | undefined): string {
  const d = toDate(v);
  return d ? format(d, "h:mm a") : "-";
}

export function formatRelative(v: string | Date | null | undefined): string {
  const d = toDate(v);
  return d ? `${formatDistanceToNowStrict(d)} ${d.getTime() > Date.now() ? "from now" : "ago"}` : "-";
}

/** "3 days left" / "closed" style countdown for deadlines. */
export function formatCountdown(v: string | Date | null | undefined): string {
  const d = toDate(v);
  if (!d) return "-";
  const ms = d.getTime() - Date.now();
  if (ms <= 0) return "Closed";
  const hours = ms / 3_600_000;
  if (hours < 1) return `${Math.max(1, Math.round(ms / 60_000))} min left`;
  if (hours < 48) return `${Math.round(hours)}h left`;
  return `${Math.round(hours / 24)} days left`;
}

export function formatNumber(n: number | null | undefined, maxFractionDigits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: maxFractionDigits }).format(n);
}

export function formatPercent(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return `${new Intl.NumberFormat("en-IN", { maximumFractionDigits: digits }).format(n)}%`;
}

export function formatCurrency(n: number | null | undefined, currency = "INR", compact = false): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
    notation: compact ? "compact" : "standard",
  }).format(n);
}

export function formatStipend(amount: number, currency = "INR"): string {
  return amount > 0 ? `${formatCurrency(amount, currency)}/mo` : "Unpaid";
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export function formatDuration(weeks: number): string {
  return `${weeks} week${weeks === 1 ? "" : "s"}`;
}

export function initials(name: string | null | undefined): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

export function humanize(s: string): string {
  return s
    .toLowerCase()
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function formatKpiValue(k: Pick<Kpi, "value" | "format">): string {
  if (typeof k.value === "string") return k.value;
  switch (k.format) {
    case "percent":
      return formatPercent(k.value);
    case "currency":
      return formatCurrency(k.value);
    case "text":
      return String(k.value);
    default:
      return formatNumber(k.value, 2);
  }
}

/** ISO datetime -> value for <input type="datetime-local"> (local zone). */
export function toDateTimeLocal(v: string | Date | null | undefined): string {
  const d = toDate(v);
  return d ? format(d, "yyyy-MM-dd'T'HH:mm") : "";
}

/** datetime-local value (local zone) -> ISO UTC with Z. */
export function fromDateTimeLocal(v: string): string {
  return new Date(v).toISOString();
}
