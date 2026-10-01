"use client";

import { X, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface BulkAction {
  label: string;
  icon?: LucideIcon;
  onClick: () => void;
  variant?: "default" | "outline" | "destructive" | "secondary";
  disabled?: boolean;
}

/** Appears when rows are selected in a DataTable. [EXT] */
export function BulkActionBar({
  count,
  actions,
  onClear,
  className,
  children,
}: {
  count: number;
  actions: BulkAction[];
  onClear?: () => void;
  className?: string;
  children?: ReactNode;
}) {
  if (count <= 0) return null;
  return (
    <div
      role="region"
      aria-label="Bulk actions"
      className={cn(
        "flex flex-wrap items-center gap-3 rounded-2xl border border-primary/20 bg-primary/5 px-4 py-2.5 text-sm animate-in fade-in slide-in-from-top-1",
        className,
      )}
    >
      <span className="font-medium">
        {count} selected
      </span>
      <div className="flex flex-wrap items-center gap-2">
        {actions.map((a) => (
          <Button key={a.label} size="sm" variant={a.variant ?? "outline"} className="rounded-lg" disabled={a.disabled} onClick={a.onClick}>
            {a.icon && <a.icon />}
            {a.label}
          </Button>
        ))}
        {children}
      </div>
      {onClear && (
        <Button size="sm" variant="ghost" className="ml-auto rounded-lg" onClick={onClear}>
          <X /> Clear
        </Button>
      )}
    </div>
  );
}
