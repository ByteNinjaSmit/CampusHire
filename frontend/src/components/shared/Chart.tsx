"use client";

import { useTheme } from "next-themes";
import { useEffect, useRef, useState } from "react";
import type { ECharts, EChartsOption } from "@/lib/echarts";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * ECharts wrapper (theme "campushire", dark variant, ResizeObserver). echarts is imported lazily
 * so it never runs on the server. Canvas renderer: tests can assert on `canvas`.
 */
export function Chart({
  option,
  height = 300,
  className,
  ariaLabel,
  onClick,
}: {
  option: EChartsOption;
  height?: number | string;
  className?: string;
  ariaLabel?: string;
  onClick?: (params: { name?: string; seriesName?: string; value?: unknown; dataIndex?: number }) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ECharts | null>(null);
  const optionRef = useRef(option);
  const clickRef = useRef(onClick);
  const { resolvedTheme } = useTheme();
  const [ready, setReady] = useState(false);
  const dark = resolvedTheme === "dark";

  useEffect(() => {
    optionRef.current = option;
    clickRef.current = onClick;
  });

  // (Re)create the instance when the theme flips.
  useEffect(() => {
    let disposed = false;
    let ro: ResizeObserver | null = null;
    const el = ref.current;
    if (!el) return;
    import("@/lib/echarts").then(({ echarts }) => {
      if (disposed || !ref.current) return;
      const chart = echarts.init(ref.current, dark ? "campushire-dark" : "campushire", { renderer: "canvas" });
      chartRef.current = chart;
      chart.setOption(optionRef.current, { notMerge: true });
      chart.on("click", (p) => clickRef.current?.(p as never));
      ro = new ResizeObserver(() => chart.resize());
      ro.observe(ref.current);
      setReady(true);
    });
    return () => {
      disposed = true;
      ro?.disconnect();
      chartRef.current?.dispose();
      chartRef.current = null;
      setReady(false);
    };
  }, [dark]);

  useEffect(() => {
    chartRef.current?.setOption(option, { notMerge: true });
  }, [option, ready]);

  return (
    <div className={cn("relative w-full", className)} style={{ height }}>
      {!ready && <Skeleton className="absolute inset-0 rounded-xl" />}
      <div ref={ref} role="img" aria-label={ariaLabel ?? "Chart"} className="size-full" />
    </div>
  );
}
