"use client";

import { ArrowDownRight, ArrowUpRight, Minus, type LucideIcon } from "lucide-react";
import { animate, useMotionValue, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";

export type StatFormat = "number" | "percent" | "currency" | "text";

function fmt(value: number | string, format: StatFormat): string {
  if (typeof value === "string") return value;
  if (format === "percent") return formatPercent(value);
  if (format === "currency") return formatCurrency(value);
  return formatNumber(value, 2);
}

function useCountUp(target: number | string, enabled: boolean) {
  const reduce = useReducedMotion();
  const mv = useMotionValue(0);
  const [display, setDisplay] = useState<number | string>(typeof target === "number" ? 0 : target);
  useEffect(() => {
    if (typeof target !== "number" || reduce || !enabled) {
      setDisplay(target);
      return;
    }
    const unsub = mv.on("change", (v) => setDisplay(Number.isInteger(target) ? Math.round(v) : Math.round(v * 100) / 100));
    const controls = animate(mv, target, { duration: 0.8, ease: "easeOut" });
    return () => {
      controls.stop();
      unsub();
    };
  }, [target, reduce, enabled, mv]);
  return display;
}

export function StatCard({
  label,
  value,
  delta,
  icon: Icon,
  format = "number",
  hint,
  className,
  animateValue = true,
}: {
  label: string;
  value: number | string;
  /** Percent change vs previous period; positive is shown green. */
  delta?: number | null;
  icon?: LucideIcon;
  format?: StatFormat;
  hint?: string;
  className?: string;
  animateValue?: boolean;
}) {
  const shown = useCountUp(value, animateValue);
  return (
    <div className={cn("card-surface relative overflow-hidden p-5", className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <p className="truncate text-sm font-medium text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold tracking-tight tabular-nums md:text-3xl">{fmt(shown, format)}</p>
        </div>
        {Icon && (
          <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Icon className="size-5" />
          </div>
        )}
      </div>
      {(delta !== undefined && delta !== null) || hint ? (
        <div className="mt-3 flex items-center gap-2 text-xs">
          {delta !== undefined && delta !== null && (
            <span
              className={cn(
                "inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 font-medium",
                delta > 0 && "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
                delta < 0 && "bg-rose-500/10 text-rose-600 dark:text-rose-400",
                delta === 0 && "bg-muted text-muted-foreground",
              )}
            >
              {delta > 0 ? <ArrowUpRight className="size-3" /> : delta < 0 ? <ArrowDownRight className="size-3" /> : <Minus className="size-3" />}
              {Math.abs(delta)}%
            </span>
          )}
          {hint && <span className="truncate text-muted-foreground">{hint}</span>}
        </div>
      ) : null}
    </div>
  );
}
