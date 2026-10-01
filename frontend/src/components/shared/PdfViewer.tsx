"use client";

import { Download, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useResumeUrl } from "@/lib/api/hooks/applications";
import { useDocumentDownloadUrl } from "@/lib/api/hooks/documents";
import { cn } from "@/lib/utils";
import { ErrorState } from "./ErrorState";

/**
 * Embeds a PDF via a short-lived presigned GET URL in an <iframe>.
 * Pass `documentId` (GET /documents/{id}/download-url) or `applicationId` (GET /applications/{id}/resume-url).
 */
export function PdfViewer({
  documentId,
  applicationId,
  height = 600,
  className,
  title = "PDF preview",
}: {
  documentId?: string;
  applicationId?: string;
  height?: number | string;
  className?: string;
  title?: string;
}) {
  const doc = useDocumentDownloadUrl(applicationId ? undefined : documentId);
  const app = useResumeUrl(applicationId);
  const q = applicationId ? app : doc;
  const url = q.data?.url;

  if (q.isError) return <ErrorState error={q.error} title="Could not load the document" onRetry={() => q.refetch()} />;
  if (q.isLoading || !url) return <Skeleton className={cn("w-full rounded-xl", className)} style={{ height }} />;

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex justify-end gap-2">
        <Button asChild variant="outline" size="sm" className="rounded-lg">
          <a href={url} target="_blank" rel="noopener noreferrer">
            <ExternalLink /> Open
          </a>
        </Button>
        <Button asChild variant="outline" size="sm" className="rounded-lg">
          <a href={url} download>
            <Download /> Download
          </a>
        </Button>
      </div>
      <iframe src={url} title={title} className="w-full rounded-xl border bg-muted/30" style={{ height }} />
    </div>
  );
}
