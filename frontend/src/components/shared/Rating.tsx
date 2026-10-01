"use client";

import { Star } from "lucide-react";
import { useId, useState, type KeyboardEvent } from "react";
import { cn } from "@/lib/utils";

/** Stars, keyboard accessible (arrow keys / 1-5 / Home / End), radiogroup semantics. */
export function RatingInput({
  value,
  onChange,
  max = 5,
  label,
  disabled,
  size = "md",
  className,
}: {
  value: number | undefined;
  onChange: (v: number) => void;
  max?: number;
  label?: string;
  disabled?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const id = useId();
  const current = hover ?? value ?? 0;
  const px = size === "sm" ? "size-5" : size === "lg" ? "size-8" : "size-6";

  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (disabled) return;
    const v = value ?? 0;
    if (e.key === "ArrowRight" || e.key === "ArrowUp") {
      e.preventDefault();
      onChange(Math.min(max, v + 1));
    } else if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
      e.preventDefault();
      onChange(Math.max(1, v - 1));
    } else if (e.key === "Home") {
      e.preventDefault();
      onChange(1);
    } else if (e.key === "End") {
      e.preventDefault();
      onChange(max);
    } else if (/^[1-9]$/.test(e.key) && Number(e.key) <= max) {
      onChange(Number(e.key));
    }
  };

  return (
    <div
      role="radiogroup"
      aria-label={label ?? "Rating"}
      aria-labelledby={undefined}
      tabIndex={disabled ? -1 : 0}
      onKeyDown={onKey}
      onMouseLeave={() => setHover(null)}
      className={cn("inline-flex items-center gap-1 rounded-lg outline-none focus-visible:ring-3 focus-visible:ring-ring/50", disabled && "opacity-60", className)}
    >
      {Array.from({ length: max }).map((_, i) => {
        const n = i + 1;
        const filled = n <= current;
        return (
          <button
            key={n}
            id={`${id}-${n}`}
            type="button"
            role="radio"
            aria-checked={value === n}
            aria-label={`${n} star${n > 1 ? "s" : ""}`}
            tabIndex={-1}
            disabled={disabled}
            onMouseEnter={() => !disabled && setHover(n)}
            onClick={() => onChange(n)}
            className="rounded-md p-0.5 transition-transform hover:scale-110 disabled:hover:scale-100"
          >
            <Star className={cn(px, "transition-colors", filled ? "fill-amber-400 text-amber-400" : "text-muted-foreground/40")} />
          </button>
        );
      })}
    </div>
  );
}

/** Read-only rating with partial fill support (e.g. 3.6). */
export function RatingDisplay({
  value,
  max = 5,
  count,
  size = "sm",
  showValue = true,
  className,
}: {
  value: number | null | undefined;
  max?: number;
  count?: number;
  size?: "xs" | "sm" | "md";
  showValue?: boolean;
  className?: string;
}) {
  const px = size === "xs" ? "size-3.5" : size === "md" ? "size-5" : "size-4";
  if (value === null || value === undefined) {
    return <span className={cn("text-xs text-muted-foreground", className)}>No ratings yet</span>;
  }
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)} aria-label={`Rated ${value.toFixed(1)} out of ${max}`}>
      <span className="inline-flex">
        {Array.from({ length: max }).map((_, i) => {
          const fill = Math.max(0, Math.min(1, value - i));
          return (
            <span key={i} className={cn("relative inline-block", px)}>
              <Star className={cn("absolute inset-0 text-muted-foreground/30", px)} />
              <span className="absolute inset-0 overflow-hidden" style={{ width: `${fill * 100}%` }}>
                <Star className={cn("fill-amber-400 text-amber-400", px)} />
              </span>
            </span>
          );
        })}
      </span>
      {showValue && <span className="text-sm font-medium tabular-nums">{value.toFixed(1)}</span>}
      {count !== undefined && <span className="text-xs text-muted-foreground">({count})</span>}
    </span>
  );
}
