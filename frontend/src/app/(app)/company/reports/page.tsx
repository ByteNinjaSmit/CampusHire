"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { ReportViewer } from "@/components/shared/ReportViewer";
import { ExportButton } from "@/components/shared/ExportButton";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { ErrorState } from "@/components/shared/ErrorState";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useReport } from "@/lib/api/hooks/reports";

const COMPANY_REPORTS = [
  { key: "posted-internships", label: "Company Postings" },
  { key: "application-review", label: "Applicant Review & Funnel" },
  { key: "student-evaluations", label: "Intern Evaluations" },
  { key: "interview-statistics", label: "Interview Metrics" },
];

export default function CompanyReportsPage() {
  const [selectedKey, setSelectedKey] = useState<string>("posted-internships");
  const { data: report, isLoading, error, refetch } = useReport(selectedKey);

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Company Analytics & Hiring Reports"
          description="Track recruitment funnel conversion, review intern scores, and export institutional PDF or Excel reports."
        />
        {report && (
          <div className="self-start sm:self-auto">
            <ExportButton reportKey={selectedKey} />
          </div>
        )}
      </div>

      <div className="border-b pb-4">
        <Tabs value={selectedKey} onValueChange={setSelectedKey}>
          <TabsList className="bg-muted/60">
            {COMPANY_REPORTS.map((r) => (
              <TabsTrigger key={r.key} value={r.key}>
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
          description="Failed to fetch analytics report data for the selected report key."
          onRetry={() => refetch()}
        />
      ) : (
        <ReportViewer report={report} />
      )}
    </div>
  );
}
