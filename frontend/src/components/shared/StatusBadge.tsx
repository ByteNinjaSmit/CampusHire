import { cn } from "@/lib/utils";
import { COLOR_CLASSES, statusMeta } from "@/lib/status";

interface StatusBadgeProps {
  status: string;
  /** Override the label (e.g. domain-specific copy). */
  label?: string;
  className?: string;
  dot?: boolean;
  size?: "sm" | "md";
}

/** Soft badge: tinted bg, colored text, 1px ring (PLAN 5.2). */
export function StatusBadge({ status, label, className, dot = true, size = "md" }: StatusBadgeProps) {
  const meta = statusMeta(status);
  const c = COLOR_CLASSES[meta.color];
  return (
    <span
      data-status={status}
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full font-medium ring-1 ring-inset",
        size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-0.5 text-xs",
        c.badge,
        className,
      )}
    >
      {dot && <span className={cn("size-1.5 rounded-full", c.dot)} />}
      {label ?? meta.label}
    </span>
  );
}
