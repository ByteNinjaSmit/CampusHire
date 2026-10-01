"use client";

import { Check, X } from "lucide-react";
import { passwordChecks, passwordStrength } from "@/lib/validation/common";
import { cn } from "@/lib/utils";

const BAR = ["bg-muted", "bg-rose-500", "bg-rose-500", "bg-amber-500", "bg-lime-500", "bg-emerald-500"];

/** Live password-strength checklist for register / reset / change-password forms. */
export function PasswordChecklist({ value, className }: { value: string; className?: string }) {
  const { score, label } = passwordStrength(value);
  return (
    <div className={cn("space-y-2 rounded-xl border bg-muted/30 p-3", className)} aria-live="polite" data-testid="password-checklist">
      <div className="flex items-center gap-2">
        <div className="flex flex-1 gap-1" aria-hidden>
          {passwordChecks.map((_, i) => (
            <span key={i} className={cn("h-1.5 flex-1 rounded-full transition-colors", i < score ? BAR[score] : "bg-muted")} />
          ))}
        </div>
        <span className="w-14 text-right text-xs font-medium text-muted-foreground">{value ? label : ""}</span>
      </div>
      <ul className="grid gap-1 text-xs sm:grid-cols-2">
        {passwordChecks.map((c) => {
          const ok = c.test(value);
          return (
            <li key={c.id} data-ok={ok} className={cn("flex items-center gap-1.5", ok ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground")}>
              {ok ? <Check className="size-3.5" /> : <X className="size-3.5" />}
              {c.label}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
