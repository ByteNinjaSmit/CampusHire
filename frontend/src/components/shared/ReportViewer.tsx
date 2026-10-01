"use client";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Kpi, ReportChart, ReportData, ReportTable } from "@/lib/api/types";
import { reportChartToOption } from "@/lib/charts";
import { formatCurrency, formatDate, formatDateTime, formatNumber, formatPercent, formatKpiValue } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Chart } from "./Chart";
import { EmptyState } from "./EmptyState";
import { StatCard } from "./StatCard";

export function KpiRow({ kpis, className }: { kpis: Kpi[]; className?: string }) {
  if (!kpis.length) return null;
  return (
    <div className={cn("grid gap-4 sm:grid-cols-2 lg:grid-cols-4", className)}>
      {kpis.map((k) => (
        <StatCard
          key={k.label}
          label={k.label}
          value={typeof k.value === "number" ? k.value : formatKpiValue(k)}
          format={k.format ?? "number"}
          delta={k.delta}
          hint={k.hint}
        />
      ))}
    </div>
  );
}

function isChartEmpty(chart: ReportChart): boolean {
  if ("data" in chart) {
    return chart.data.length === 0 || chart.data.every((d) => d.value === 0);
  }
  if (chart.type === "radar") {
    return chart.series.length === 0;
  }
  return chart.series.length === 0 || chart.series.every((s: { data: number[] }) => s.data.every((v: number) => !v));
}

export function ReportChartCard({ chart, height = 300, className }: { chart: ReportChart; height?: number; className?: string }) {
  const empty = isChartEmpty(chart);
  return (
    <section className={cn("card-surface p-5", className)} data-chart-id={chart.id}>
      <h3 className="mb-3 text-sm font-semibold">{chart.title}</h3>
      {empty ? (
        <div className="flex items-center justify-center text-sm text-muted-foreground" style={{ height }}>
          No data for this period
        </div>
      ) : (
        <Chart option={reportChartToOption(chart)} height={height} ariaLabel={chart.title} />
      )}
    </section>
  );
}

function formatCell(v: string | number | null | undefined, format: ReportTable["columns"][number]["format"]): string {
  if (v === null || v === undefined || v === "") return "-";
  switch (format) {
    case "number":
      return typeof v === "number" ? formatNumber(v, 2) : String(v);
    case "percent":
      return typeof v === "number" ? formatPercent(v) : String(v);
    case "currency":
      return typeof v === "number" ? formatCurrency(v) : String(v);
    case "date":
      return formatDate(String(v));
    case "datetime":
      return formatDateTime(String(v));
    default:
      return String(v);
  }
}

export function ReportTableCard({ table, className }: { table: ReportTable; className?: string }) {
  return (
    <section className={cn("card-surface overflow-hidden", className)} data-table-id={table.id}>
      <h3 className="border-b px-5 py-3 text-sm font-semibold">{table.title}</h3>
      {table.rows.length === 0 ? (
        <div className="p-6">
          <EmptyState title="No rows" description="Nothing to show for the selected period." compact />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                {table.columns.map((c) => (
                  <TableHead key={c.key} className={cn("whitespace-nowrap text-xs font-semibold uppercase tracking-wide text-muted-foreground", (c.format === "number" || c.format === "percent" || c.format === "currency") && "text-right")}>
                    {c.label}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {table.rows.map((r, i) => (
                <TableRow key={i}>
                  {table.columns.map((c) => (
                    <TableCell key={c.key} className={cn((c.format === "number" || c.format === "percent" || c.format === "currency") && "text-right tabular-nums")}>
                      {formatCell(r[c.key], c.format)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </section>
  );
}

/** KPI row + charts + tables for any ReportData (used by every report page). */
export function ReportViewer({ report, className }: { report: ReportData; className?: string }) {
  return (
    <div className={cn("space-y-6", className)}>
      <KpiRow kpis={report.kpis} />
      {report.charts.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-2">
          {report.charts.map((c) => (
            <ReportChartCard key={c.id} chart={c} />
          ))}
        </div>
      )}
      {report.tables.map((t) => (
        <ReportTableCard key={t.id} table={t} />
      ))}
      <p className="text-xs text-muted-foreground">Generated {formatDateTime(report.generated_at)}</p>
    </div>
  );
}
