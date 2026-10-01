"use client";

import { useEffect, useState } from "react";
import { Slider } from "@/components/ui/slider";
import { cn } from "@/lib/utils";

/** Two-thumb range slider; commits on release (onValueCommit) while previewing live. */
export function RangeSlider({
  min,
  max,
  step = 1,
  value,
  onChange,
  formatValue = (n) => String(n),
  label,
  className,
}: {
  min: number;
  max: number;
  step?: number;
  value: [number, number];
  onChange: (v: [number, number]) => void;
  formatValue?: (n: number) => string;
  label?: string;
  className?: string;
}) {
  const [local, setLocal] = useState<[number, number]>(value);
  useEffect(() => setLocal(value), [value[0], value[1]]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className={cn("space-y-3", className)}>
      {label && (
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium">{label}</span>
          <span className="tabular-nums text-muted-foreground">
            {formatValue(local[0])} - {formatValue(local[1])}
          </span>
        </div>
      )}
      <Slider
        aria-label={label ?? "Range"}
        min={min}
        max={Math.max(max, min + step)}
        step={step}
        value={local}
        onValueChange={(v) => setLocal([v[0], v[1]] as [number, number])}
        onValueCommit={(v) => onChange([v[0], v[1]] as [number, number])}
      />
    </div>
  );
}
