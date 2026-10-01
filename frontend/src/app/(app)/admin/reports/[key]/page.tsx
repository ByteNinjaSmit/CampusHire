"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { PageHeader } from "@/components/shared/PageHeader";
import { ReportViewer } from "@/components/shared/ReportViewer";
import { ExportButton } from "@/components/shared/ExportButton";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { ErrorState } from "@/components/shared/ErrorState";
import { useReport } from "@/lib/api/hooks/reports";
import { ArrowLeft } from "lucide-react";

export default function AdminReportDetailPage() {
  const params = useParams();
  const key = typeof params?.key === "string" ? params.key : "";
  const { data: report, isLoading, error, refetch } = useReport(key);

  return (
    <div className="space-y-8">
      <div>
        <Link
          href="/admin/reports"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-3 transition-colors"
        >
          <ArrowLeft className="size-3.5" /> Back to all reports
        </Link>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <PageHeader
            title={report?.title || "Institutional Report"}
            description="Detailed campus analytics with full table breakdowns and export options."
          />
          {report && (
            <div className="self-start sm:self-auto">
              <ExportButton reportKey={key} />
            </div>
          )}
        </div>
      </div>

      {isLoading ? (
        <LoadingCardGrid count={3} />
      ) : error || !report ? (
        <ErrorState
          title="Could not load report"
          description="Failed to fetch report data for the specified key."
          onRetry={() => refetch()}
        />
      ) : (
        <ReportViewer report={report} />
      )}
    </div>
  );
}
