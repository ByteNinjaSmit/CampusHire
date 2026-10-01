"use client";

import { Download, FileSpreadsheet, FileText, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Progress } from "@/components/ui/progress";
import { useExportReport, useJob } from "@/lib/api/hooks/reports";
import type { ReportParams } from "@/lib/api/types-extra";
import { errorMessage } from "@/lib/forms";

/** Creates an export job, polls /jobs/{id} every 2 s (the realtime socket also updates it), then downloads the file. */
export function ExportButton({
  reportKey,
  params,
  formats = ["pdf", "xlsx"],
  label = "Export",
}: {
  reportKey: string;
  params?: ReportParams;
  formats?: ("pdf" | "xlsx")[];
  label?: string;
}) {
  const exportReport = useExportReport();
  const [jobId, setJobId] = useState<string | undefined>();
  const job = useJob(jobId).data;
  const handled = useRef<string | null>(null);

  useEffect(() => {
    if (!job || handled.current === job.id) return;
    if (job.status === "SUCCEEDED") {
      handled.current = job.id;
      if (job.download_url) {
        const a = document.createElement("a");
        a.href = job.download_url;
        a.rel = "noopener";
        a.download = "";
        document.body.appendChild(a);
        a.click();
        a.remove();
        toast.success("Export ready", { description: "Your download has started." });
      } else {
        toast.success("Export finished");
      }
      setJobId(undefined);
    } else if (job.status === "FAILED") {
      handled.current = job.id;
      toast.error("Export failed", { description: job.error ?? undefined });
      setJobId(undefined);
    }
  }, [job]);

  const running = exportReport.isPending || (!!jobId && (!job || job.status === "QUEUED" || job.status === "RUNNING"));

  const start = (format: "pdf" | "xlsx") => {
    exportReport.mutate(
      { key: reportKey, body: { format, params: params as Record<string, unknown> | undefined } },
      {
        onSuccess: (j) => {
          handled.current = null;
          setJobId(j.id);
          toast.info(`Generating ${format.toUpperCase()}...`);
        },
        onError: (e) => toast.error(errorMessage(e, "Could not start the export")),
      },
    );
  };

  return (
    <div className="flex items-center gap-3">
      {running && job && (
        <div className="hidden w-28 sm:block" aria-label="Export progress">
          <Progress value={job.progress} className="h-1.5" />
        </div>
      )}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" className="rounded-xl" disabled={running} data-testid="export-button">
            {running ? <Loader2 className="animate-spin" /> : <Download />}
            {running ? "Exporting..." : label}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="rounded-xl">
          {formats.includes("pdf") && (
            <DropdownMenuItem onSelect={() => start("pdf")}>
              <FileText /> Export as PDF
            </DropdownMenuItem>
          )}
          {formats.includes("xlsx") && (
            <DropdownMenuItem onSelect={() => start("xlsx")}>
              <FileSpreadsheet /> Export as Excel
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
