"use client";

import { useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { SearchInput } from "@/components/shared/SearchInput";
import { LoadingTableSkeleton } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useApplications } from "@/lib/api/hooks/applications";
import { formatDate, formatRelativeDate } from "@/lib/format";
import type { ApplicationStatus } from "@/lib/api/types";
import { Briefcase, Building2, Calendar, ArrowRight, Eye } from "lucide-react";

export default function StudentApplicationsPage() {
  const [statusTab, setStatusTab] = useState<string>("ALL");
  const [search, setSearch] = useState("");

  const { data, isLoading } = useApplications({
    status: statusTab !== "ALL" ? (statusTab as ApplicationStatus) : undefined,
    page: 1,
    page_size: 50,
  });

  const applications = (data?.items ?? []).filter((app) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      app.internship?.title?.toLowerCase().includes(q) ||
      app.internship?.company_name?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="My Applications"
          description="View and track your submitted internship applications and recruitment stages."
        />
        <Button asChild className="rounded-xl">
          <Link href="/internships">Apply to More Internships</Link>
        </Button>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <Tabs value={statusTab} onValueChange={setStatusTab} className="w-auto">
          <TabsList className="bg-muted/60">
            <TabsTrigger value="ALL">All ({data?.total ?? 0})</TabsTrigger>
            <TabsTrigger value="PENDING">Pending</TabsTrigger>
            <TabsTrigger value="UNDER_REVIEW">Reviewing</TabsTrigger>
            <TabsTrigger value="INTERVIEW">Interview</TabsTrigger>
            <TabsTrigger value="ACCEPTED">Accepted</TabsTrigger>
            <TabsTrigger value="REJECTED">Rejected</TabsTrigger>
          </TabsList>
        </Tabs>

        <div className="w-full sm:w-72">
          <SearchInput value={search} onChange={setSearch} placeholder="Search applications..." />
        </div>
      </div>

      {isLoading ? (
        <LoadingTableSkeleton rows={5} />
      ) : applications.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          title="No applications found"
          description={
            statusTab !== "ALL"
              ? `No applications currently in "${statusTab.replace("_", " ")}" status.`
              : "You haven't submitted any internship applications yet."
          }
          action={
            <Button asChild className="rounded-xl">
              <Link href="/internships">Explore Opportunities</Link>
            </Button>
          }
        />
      ) : (
        <div className="divide-y divide-border/60 rounded-2xl border border-border/60 bg-card shadow-sm">
          {applications.map((app) => (
            <div
              key={app.id}
              className="flex flex-col gap-4 p-5 transition-colors hover:bg-muted/30 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="flex items-start gap-4">
                <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold shadow-xs">
                  {app.internship?.company_name?.[0]?.toUpperCase() || <Building2 className="size-6" />}
                </div>

                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-muted-foreground uppercase">
                      {app.internship?.company_name || "Company"}
                    </span>
                    <StatusBadge status={app.status} />
                  </div>

                  <h3 className="font-semibold text-base text-foreground hover:text-primary transition-colors">
                    <Link href={`/student/applications/${app.id}`}>
                      {app.internship?.title || "Internship Role"}
                    </Link>
                  </h3>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                    <span>Applied {formatRelativeDate(app.created_at)}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 self-end sm:self-center">
                <Button size="sm" asChild variant="outline" className="rounded-xl gap-1.5 text-xs">
                  <Link href={`/student/applications/${app.id}`}>
                    <Eye className="size-3.5" /> View Details
                  </Link>
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
