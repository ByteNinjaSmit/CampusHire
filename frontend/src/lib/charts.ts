import type { EChartsOption } from "@/lib/echarts";
import type { ReportChart } from "@/lib/api/types";

const PALETTE = ["#6366F1", "#22C55E", "#F59E0B", "#06B6D4", "#EC4899", "#8B5CF6", "#64748B"];

/** Converts a ReportChart (PLAN 6.11) into an ECharts option. Theme colors come from the registered theme. */
export function reportChartToOption(chart: ReportChart): EChartsOption {
  switch (chart.type) {
    case "line":
    case "area":
    case "bar": {
      const multi = chart.series.length > 1;
      return {
        color: PALETTE,
        tooltip: { trigger: "axis", axisPointer: { type: chart.type === "bar" ? "shadow" : "line" } },
        legend: multi ? { top: 0, type: "scroll" } : undefined,
        grid: { left: 8, right: 16, top: multi ? 36 : 16, bottom: 8, containLabel: true },
        xAxis: { type: "category", data: chart.x, boundaryGap: chart.type === "bar", axisLabel: { hideOverlap: true } },
        yAxis: { type: "value", minInterval: 1 },
        series: chart.series.map((s) => ({
          name: s.name,
          type: chart.type === "bar" ? "bar" : "line",
          data: s.data,
          smooth: chart.type !== "bar",
          showSymbol: chart.type === "line" ? chart.x.length < 20 : false,
          areaStyle: chart.type === "area" ? { opacity: 0.18 } : undefined,
          barMaxWidth: 36,
          itemStyle: chart.type === "bar" ? { borderRadius: [6, 6, 0, 0] } : undefined,
          emphasis: { focus: "series" },
        })),
      } as EChartsOption;
    }
    case "pie":
    case "donut":
      return {
        color: PALETTE,
        tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
        legend: { bottom: 0, type: "scroll" },
        series: [
          {
            type: "pie",
            radius: chart.type === "donut" ? ["52%", "74%"] : ["0%", "72%"],
            center: ["50%", "44%"],
            avoidLabelOverlap: true,
            itemStyle: { borderRadius: 6, borderColor: "transparent", borderWidth: 2 },
            label: { show: false },
            emphasis: { label: { show: true, fontWeight: "bold" } },
            data: chart.data,
          },
        ],
      } as EChartsOption;
    case "radar":
      return {
        color: PALETTE,
        tooltip: {},
        legend: chart.series.length > 1 ? { bottom: 0 } : undefined,
        radar: { indicator: chart.indicators, radius: "62%", center: ["50%", "48%"] },
        series: [
          {
            type: "radar",
            data: chart.series.map((s) => ({ name: s.name, value: s.data, areaStyle: { opacity: 0.15 } })),
          },
        ],
      } as EChartsOption;
  }
}
