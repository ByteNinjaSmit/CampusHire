// Tree-shaken ECharts registration. Import this module ONLY from client code, lazily (see components/shared/Chart.tsx).
import { BarChart, LineChart, PieChart, RadarChart } from "echarts/charts";
import {
  AriaComponent,
  GridComponent,
  LegendComponent,
  RadarComponent,
  TitleComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  RadarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  RadarComponent,
  AriaComponent,
  CanvasRenderer,
]);

export const CHART_COLORS = ["#6366F1", "#22C55E", "#F59E0B", "#06B6D4", "#EC4899", "#8B5CF6", "#64748B"];

function theme(dark: boolean) {
  const text = dark ? "#a1a1aa" : "#52525b";
  const axis = dark ? "rgba(255,255,255,0.14)" : "#d4d4d8";
  const split = dark ? "rgba(255,255,255,0.07)" : "#f4f4f5";
  const axisCfg = {
    axisLine: { lineStyle: { color: axis } },
    axisTick: { lineStyle: { color: axis } },
    axisLabel: { color: text },
    splitLine: { lineStyle: { color: split } },
    nameTextStyle: { color: text },
  };
  return {
    color: CHART_COLORS,
    backgroundColor: "transparent",
    textStyle: { fontFamily: "var(--font-geist-sans), system-ui, sans-serif", color: text },
    title: { textStyle: { color: dark ? "#fafafa" : "#18181b" }, subtextStyle: { color: text } },
    legend: { textStyle: { color: text } },
    categoryAxis: axisCfg,
    valueAxis: axisCfg,
    timeAxis: axisCfg,
    logAxis: axisCfg,
    radar: { axisLine: { lineStyle: { color: axis } }, splitLine: { lineStyle: { color: axis } }, splitArea: { show: false }, axisName: { color: text } },
    tooltip: {
      backgroundColor: dark ? "#27272a" : "#ffffff",
      borderColor: dark ? "rgba(255,255,255,0.12)" : "#e4e4e7",
      textStyle: { color: dark ? "#fafafa" : "#18181b" },
      extraCssText: "border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.12);",
    },
  };
}

echarts.registerTheme("campushire", theme(false));
echarts.registerTheme("campushire-dark", theme(true));

export { echarts };
export type ECharts = ReturnType<typeof echarts.init>;
export type EChartsOption = Parameters<ECharts["setOption"]>[0];
