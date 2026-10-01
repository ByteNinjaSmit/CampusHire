"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { ReportViewer } from "@/components/shared/ReportViewer";
import { ExportButton } from "@/components/shared/ExportButton";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { ErrorState } from "@/components/shared/ErrorState";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useReport } from "@/lib/api/hooks/reports";

export const ADMIN_REPORTS = [
  { key: "placement-summary", label: "Placement Summary" },
  { key: "application-analytics", label: "Application Analytics" },
  { key: "student-performance", label: "Student Performance" },
  { key: "company-statistics", label: "Company Statistics" },
  { key: "system-activity", label: "System Activity" },
  { key: "compliance", label: "Compliance & Auditing" },
];

export default function AdminReportsPage() {
  const [selectedKey, setSelectedKey] = useState<string>("placement-summary");
  const { data: report, isLoading, error, refetch } = useReport(selectedKey);

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Institutional Reports & Placement Intelligence"
          description="In-depth analytics on campus placement metrics, hiring funnels, company engagement, and system performance."
        />
        {report && (
          <div className="self-start sm:self-auto">
            <ExportButton reportKey={selectedKey} />
          </div>
        )}
      </div>

      <div className="border-b pb-4">
        <Tabs value={selectedKey} onValueChange={setSelectedKey}>
          <TabsList className="bg-muted/60 flex-wrap h-auto gap-1">
            {ADMIN_REPORTS.map((r) => (
              <TabsTrigger key={r.key} value={r.key} className="text-xs">
                {r.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      {isLoading ? (
        <LoadingCardGrid count={3} />
      ) : error || !report ? (
        <ErrorState
          title="Could not load report"
          description="Failed to fetch report data for the selected report key."
          onRetry={() => refetch()}
        />
      ) : (
        <ReportViewer report={report} />
      )}
    </div>
  );
}
