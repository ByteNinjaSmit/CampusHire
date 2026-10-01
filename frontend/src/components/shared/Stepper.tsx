import { Check } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface StepperStep {
  id?: string;
  label: string;
  description?: ReactNode;
  /** Mark the step as failed/terminal (e.g. rejected). */
  state?: "error";
}

/**
 * Stepper: steps before `current` are complete, `current` is active, later steps are upcoming.
 * Use `current = -1` for none active and `current = steps.length` for all complete.
 */
export function Stepper({
  steps,
  current,
  orientation = "horizontal",
  className,
}: {
  steps: StepperStep[];
  current: number;
  orientation?: "horizontal" | "vertical";
  className?: string;
}) {
  const vertical = orientation === "vertical";
  return (
    <ol className={cn(vertical ? "flex flex-col" : "flex w-full items-start", className)} aria-label="Progress">
      {steps.map((s, i) => {
        const done = i < current;
        const active = i === current;
        const error = s.state === "error";
        const last = i === steps.length - 1;
        const circle = (
          <span
            aria-hidden
            className={cn(
              "flex size-8 shrink-0 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors",
              error && "border-rose-500 bg-rose-500 text-white",
              !error && done && "border-primary bg-primary text-primary-foreground",
              !error && active && "border-primary bg-background text-primary ring-4 ring-primary/15",
              !error && !done && !active && "border-border bg-background text-muted-foreground",
            )}
          >
            {done && !error ? <Check className="size-4" /> : error ? "!" : i + 1}
          </span>
        );
        const text = (
          <div className={cn(vertical ? "pb-6" : "mt-2 px-1 text-center")}>
            <p className={cn("text-sm font-medium", !done && !active && !error && "text-muted-foreground")}>{s.label}</p>
            {s.description && <p className="mt-0.5 text-xs text-muted-foreground">{s.description}</p>}
          </div>
        );
        if (vertical) {
          return (
            <li key={s.id ?? s.label} className="relative flex gap-3" aria-current={active ? "step" : undefined}>
              <div className="flex flex-col items-center">
                {circle}
                {!last && <span className={cn("mt-1 w-0.5 flex-1", done ? "bg-primary" : "bg-border")} />}
              </div>
              {text}
            </li>
          );
        }
        return (
          <li key={s.id ?? s.label} className="relative flex flex-1 flex-col items-center" aria-current={active ? "step" : undefined}>
            <div className="flex w-full items-center">
              <span className={cn("h-0.5 flex-1", i === 0 ? "bg-transparent" : done || active ? "bg-primary" : "bg-border")} />
              {circle}
              <span className={cn("h-0.5 flex-1", last ? "bg-transparent" : done ? "bg-primary" : "bg-border")} />
            </div>
            {text}
          </li>
        );
      })}
    </ol>
  );
}
