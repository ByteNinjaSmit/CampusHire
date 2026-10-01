"use client";

import { Slider } from "@/components/ui/slider";
import { cn } from "@/lib/utils";
import type { EvaluationCriterion } from "@/lib/api/types";

/** One slider per evaluation criterion (0..max_score). Shows weight and live score. */
export function ScoreSlider({
  criterion,
  value,
  onChange,
  disabled,
  className,
}: {
  criterion: Pick<EvaluationCriterion, "name" | "description" | "weight" | "max_score">;
  value: number;
  onChange: (v: number) => void;
  disabled?: boolean;
  className?: string;
}) {
  const pct = (value / criterion.max_score) * 100;
  return (
    <div className={cn("space-y-2 rounded-xl border bg-card p-3", className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium">{criterion.name}</p>
          {criterion.description && <p className="text-xs text-muted-foreground">{criterion.description}</p>}
        </div>
        <div className="shrink-0 text-right">
          <p className="text-lg font-semibold tabular-nums leading-none">
            {value}
            <span className="text-sm font-normal text-muted-foreground"> / {criterion.max_score}</span>
          </p>
          <p className="text-[11px] text-muted-foreground">weight {criterion.weight}</p>
        </div>
      </div>
      <Slider
        aria-label={`${criterion.name} score`}
        min={0}
        max={criterion.max_score}
        step={1}
        value={[value]}
        disabled={disabled}
        onValueChange={(v) => onChange(v[0] ?? 0)}
      />
      <div className="flex justify-between text-[10px] text-muted-foreground" aria-hidden>
        {Array.from({ length: criterion.max_score + 1 }).map((_, i) => (
          <span key={i}>{i}</span>
        ))}
      </div>
      <span className="sr-only">{Math.round(pct)} percent</span>
    </div>
  );
}

/** weighted_score = 100 * sum(score/max * weight) / sum(weight), rounded to 2 decimals (PLAN 6.7). */
export function computeWeightedScore(
  criteria: Pick<EvaluationCriterion, "weight" | "max_score" | "id">[],
  scores: Record<string, number>,
): number {
  const totalWeight = criteria.reduce((a, c) => a + c.weight, 0);
  if (totalWeight <= 0) return 0;
  const sum = criteria.reduce((a, c) => a + ((scores[c.id] ?? 0) / c.max_score) * c.weight, 0);
  return Math.round((100 * sum) / totalWeight * 100) / 100;
}
