"use client";

import { Loader2 } from "lucide-react";
import { useState, type ReactNode } from "react";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  destructive,
  onConfirm,
  loading,
  reasonLabel,
  reasonRequired,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: ReactNode;
  confirmLabel?: string;
  destructive?: boolean;
  /** Receives the typed reason when `reasonLabel` is set. May return a promise; the dialog closes after it resolves. */
  onConfirm: (reason?: string) => void | Promise<unknown>;
  loading?: boolean;
  /** Show a textarea to collect a reason (deactivate / reject / cancel flows). */
  reasonLabel?: string;
  reasonRequired?: boolean;
  children?: ReactNode;
}) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const isBusy = loading || busy;
  const blocked = !!reasonLabel && !!reasonRequired && reason.trim().length < 3;

  async function run() {
    setBusy(true);
    try {
      await onConfirm(reasonLabel ? reason.trim() : undefined);
      setReason("");
      onOpenChange(false);
    } catch {
      // caller handles/toasts the error; keep the dialog open
    } finally {
      setBusy(false);
    }
  }

  return (
    <AlertDialog
      open={open}
      onOpenChange={(o) => {
        if (isBusy) return;
        onOpenChange(o);
        if (!o) setReason("");
      }}
    >
      <AlertDialogContent className="rounded-2xl">
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          {description && <AlertDialogDescription>{description}</AlertDialogDescription>}
        </AlertDialogHeader>
        {children}
        {reasonLabel && (
          <div className="space-y-1.5">
            <label className="text-sm font-medium" htmlFor="confirm-reason">
              {reasonLabel}
              {reasonRequired ? " *" : ""}
            </label>
            <Textarea
              id="confirm-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              maxLength={500}
              className="rounded-xl"
            />
          </div>
        )}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isBusy} className="rounded-xl">
            Cancel
          </AlertDialogCancel>
          <Button variant={destructive ? "destructive" : "default"} className="rounded-xl" disabled={isBusy || blocked} onClick={run}>
            {isBusy && <Loader2 className="animate-spin" />}
            {confirmLabel}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
