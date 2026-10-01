"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { ReportViewer } from "@/components/shared/ReportViewer";
import { ExportButton } from "@/components/shared/ExportButton";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { ErrorState } from "@/components/shared/ErrorState";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { useReport } from "@/lib/api/hooks/reports";

const STUDENT_REPORTS = [
  { key: "my-applications", label: "My Applications" },
  { key: "interview-schedule", label: "Interview Schedule" },
  { key: "placement-status", label: "Placement Status" },
];

export default function StudentReportsPage() {
  const [selectedKey, setSelectedKey] = useState<string>("my-applications");
  const { data: report, isLoading, error, refetch } = useReport(selectedKey);

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Personal Reports & Analytics"
          description="Generate and export comprehensive summaries of your application lifecycle, interviews, and placement outcomes."
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
            {STUDENT_REPORTS.map((r) => (
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
          description="Failed to fetch report data for the selected report."
          onRetry={() => refetch()}
        />
      ) : (
        <ReportViewer report={report} />
      )}
    </div>
  );
}
