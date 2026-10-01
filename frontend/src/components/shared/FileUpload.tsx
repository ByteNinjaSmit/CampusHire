"use client";

import { CheckCircle2, FileText, Loader2, UploadCloud, X } from "lucide-react";
import { useCallback, useRef, useState, type DragEvent } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { uploadDocument } from "@/lib/api/endpoints/documents";
import { qk } from "@/lib/api/keys";
import type { Document, DocumentKind } from "@/lib/api/types";
import { errorMessage } from "@/lib/forms";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";

const FIVE_MB = 5 * 1024 * 1024;

async function looksLikePdf(file: File): Promise<boolean> {
  try {
    const head = await file.slice(0, 5).text();
    return head === "%PDF-";
  } catch {
    return true; // cannot read; let the server decide
  }
}

/**
 * Presigned-POST upload (PLAN 5.3): validate -> request ticket -> POST FormData to MinIO with progress (XHR) -> /complete.
 * The client enforces application/pdf and <= maxBytes first (spec V4); the server re-checks size and the `%PDF-` magic.
 */
export function FileUpload({
  kind,
  accept = "application/pdf",
  maxBytes = FIVE_MB,
  onUploaded,
  label,
  hint,
  className,
  disabled,
}: {
  kind: DocumentKind;
  accept?: string;
  maxBytes?: number;
  onUploaded: (doc: Document) => void;
  label?: string;
  hint?: string;
  className?: string;
  disabled?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const qc = useQueryClient();
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState<"idle" | "uploading" | "finalizing" | "done" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  const accepted = accept.split(",").map((s) => s.trim().toLowerCase());
  const isPdfOnly = accepted.length === 1 && accepted[0] === "application/pdf";
  const mb = Math.round(maxBytes / 1024 / 1024);

  const start = useCallback(
    async (f: File) => {
      setError(null);
      setFile(f);
      setProgress(0);

      const typeOk =
        accepted.includes(f.type.toLowerCase()) ||
        accepted.some((a) => a.startsWith(".") && f.name.toLowerCase().endsWith(a)) ||
        accepted.some((a) => a.endsWith("/*") && f.type.startsWith(a.slice(0, -1)));
      if (!typeOk) {
        setPhase("error");
        setError(isPdfOnly ? "Only PDF files are allowed." : "This file type is not allowed.");
        return;
      }
      if (f.size <= 0) {
        setPhase("error");
        setError("The file is empty.");
        return;
      }
      if (f.size > maxBytes) {
        setPhase("error");
        setError(`File is too large (${formatBytes(f.size)}). Maximum is ${mb} MB.`);
        return;
      }
      if (f.type === "application/pdf" && !(await looksLikePdf(f))) {
        setPhase("error");
        setError("This file does not look like a valid PDF.");
        return;
      }

      const ac = new AbortController();
      abortRef.current = ac;
      setPhase("uploading");
      try {
        const doc = await uploadDocument(
          f,
          kind,
          (p) => {
            setProgress(p.percent);
            if (p.percent >= 100) setPhase("finalizing");
          },
          ac.signal,
        );
        setPhase("done");
        qc.invalidateQueries({ queryKey: qk.documents.all });
        onUploaded(doc);
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") {
          setPhase("idle");
          setFile(null);
          return;
        }
        setPhase("error");
        setError(errorMessage(e, "Upload failed"));
      } finally {
        abortRef.current = null;
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [kind, maxBytes, onUploaded, qc, accept],
  );

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (disabled || phase === "uploading") return;
    const f = e.dataTransfer.files?.[0];
    if (f) void start(f);
  };

  const busy = phase === "uploading" || phase === "finalizing";

  return (
    <div className={cn("space-y-3", className)}>
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled || busy}
        aria-label={label ?? "Upload a file"}
        onClick={() => !disabled && !busy && inputRef.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && !disabled && !busy && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled && !busy) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed px-6 py-8 text-center outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/50",
          dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50 hover:bg-muted/30",
          (disabled || busy) && "cursor-not-allowed opacity-60",
          phase === "error" && "border-destructive/40",
        )}
      >
        <div className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
          {busy ? <Loader2 className="size-5 animate-spin" /> : phase === "done" ? <CheckCircle2 className="size-5" /> : <UploadCloud className="size-5" />}
        </div>
        <p className="text-sm font-medium">{label ?? (isPdfOnly ? "Drop your PDF here or click to browse" : "Drop a file here or click to browse")}</p>
        <p className="text-xs text-muted-foreground">{hint ?? `${isPdfOnly ? "PDF only" : accept}, up to ${mb} MB`}</p>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="sr-only"
          data-testid="file-upload-input"
          disabled={disabled || busy}
          onChange={(e) => {
            const f = e.target.files?.[0];
            e.target.value = "";
            if (f) void start(f);
          }}
        />
      </div>

      {file && phase !== "idle" && (
        <div className="rounded-xl border bg-card p-3" aria-live="polite">
          <div className="flex items-center gap-3">
            <FileText className="size-5 shrink-0 text-muted-foreground" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{file.name}</p>
              <p className="text-xs text-muted-foreground">
                {formatBytes(file.size)}
                {phase === "uploading" && ` - uploading ${progress}%`}
                {phase === "finalizing" && " - verifying..."}
                {phase === "done" && " - uploaded"}
              </p>
            </div>
            {busy && (
              <Button type="button" variant="ghost" size="icon-sm" aria-label="Cancel upload" onClick={() => abortRef.current?.abort()}>
                <X />
              </Button>
            )}
          </div>
          {busy && <Progress value={progress} className="mt-2 h-1.5" />}
          {phase === "error" && error && (
            <p role="alert" className="mt-2 text-sm text-destructive">
              {error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
