"use client";

import { AlertTriangle, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/forms";
import { cn } from "@/lib/utils";

export function ErrorState({
  error,
  title = "Something went wrong",
  onRetry,
  className,
}: {
  error?: unknown;
  title?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-2xl border border-destructive/20 bg-destructive/5 px-6 py-12 text-center",
        className,
      )}
      role="alert"
    >
      <div className="mb-3 flex size-11 items-center justify-center rounded-2xl bg-destructive/10 text-destructive">
        <AlertTriangle className="size-5" />
      </div>
      <h3 className="font-semibold">{title}</h3>
      {error ? <p className="mt-1 max-w-md text-sm text-muted-foreground">{errorMessage(error)}</p> : null}
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-4 rounded-xl" onClick={onRetry}>
          <RotateCw /> Try again
        </Button>
      )}
    </div>
  );
}
