import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function AuthHeading({ title, description, className }: { title: string; description?: ReactNode; className?: string }) {
  return (
    <div className={cn("mb-6 space-y-1.5", className)}>
      <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">{title}</h1>
      {description && <p className="text-sm text-muted-foreground md:text-base">{description}</p>}
    </div>
  );
}
