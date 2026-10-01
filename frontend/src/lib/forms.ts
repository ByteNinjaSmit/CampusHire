import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { toast } from "sonner";
import { ApiError } from "@/lib/api/client";

/**
 * Maps ApiError.details to RHF setError(field). Returns true when at least one field error was set.
 * Falls back to a toast with the error message when nothing maps.
 */
export function applyApiErrors<T extends FieldValues>(err: unknown, setError: UseFormSetError<T>, knownFields?: string[]): boolean {
  if (!(err instanceof ApiError)) {
    toast.error(err instanceof Error ? err.message : "Something went wrong");
    return false;
  }
  const map = err.fieldErrors;
  let applied = false;
  for (const [field, message] of Object.entries(map)) {
    if (knownFields && !knownFields.includes(field)) continue;
    setError(field as Path<T>, { type: "server", message });
    applied = true;
  }
  if (!applied) toast.error(errorMessage(err));
  return applied;
}

export function errorMessage(err: unknown, fallback = "Something went wrong"): string {
  if (err instanceof ApiError) {
    switch (err.code) {
      case "RATE_LIMITED":
        return "Too many attempts. Please wait a moment and try again.";
      case "NETWORK":
        return "Cannot reach the server.";
      default:
        return err.message || fallback;
    }
  }
  if (err instanceof TypeError) return "Cannot reach the server. Check your connection and try again.";
  return err instanceof Error ? err.message : fallback;
}
