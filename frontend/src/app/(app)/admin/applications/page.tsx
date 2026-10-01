"use client";

import { useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { SearchInput } from "@/components/shared/SearchInput";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingTableSkeleton } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useApplications } from "@/lib/api/hooks/applications";
import { formatDate, formatRelativeDate } from "@/lib/format";
import type { ApplicationStatus } from "@/lib/api/types";
import {
  Inbox,
  User,
  Briefcase,
  GraduationCap,
  Calendar,
  Eye,
  CheckCircle2,
  Clock,
} from "lucide-react";

export default function AdminApplicationsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useApplications({
    status: statusFilter !== "ALL" ? (statusFilter as ApplicationStatus) : undefined,
    page,
    page_size: 30,
  });

  const applications = (data?.items ?? []).filter((app) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      app.student?.full_name?.toLowerCase().includes(q) ||
      app.student?.department?.toLowerCase().includes(q) ||
      app.internship?.title?.toLowerCase().includes(q) ||
      app.internship?.company?.name?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Campus-wide Applications Oversight"
          description="Monitor recruitment progress across all departments, tracking student candidates from application to final placement."
        />
      </div>

      {/* Filters and Search Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="w-48">
          <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1); }}>
            <SelectTrigger className="rounded-xl">
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent className="rounded-xl">
              <SelectItem value="ALL">All Statuses ({data?.total ?? 0})</SelectItem>
              <SelectItem value="PENDING">Pending</SelectItem>
              <SelectItem value="UNDER_REVIEW">Under Review</SelectItem>
              <SelectItem value="SHORTLISTED">Shortlisted</SelectItem>
              <SelectItem value="INTERVIEW">Interview</SelectItem>
              <SelectItem value="ACCEPTED">Accepted / Placed</SelectItem>
              <SelectItem value="REJECTED">Rejected</SelectItem>
              <SelectItem value="WITHDRAWN">Withdrawn</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="w-full sm:w-72">
          <SearchInput
            value={search}
            onChange={(v) => { setSearch(v); setPage(1); }}
            placeholder="Search candidate or role..."
          />
        </div>
      </div>

      {/* Applications List */}
      {isLoading ? (
        <LoadingTableSkeleton rows={8} />
      ) : applications.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title="No applications found"
          description="No candidate applications match your current search and filter criteria."
        />
      ) : (
        <div className="divide-y divide-border/60 rounded-2xl border border-border/60 bg-card shadow-sm overflow-hidden">
          <div className="flex items-center justify-between p-3.5 bg-muted/30 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            <span>Candidate & Department</span>
            <div className="flex items-center gap-16 pr-4">
              <span>Target Role</span>
              <span>Status</span>
              <span>Applied</span>
              <span>Review</span>
            </div>
          </div>

          {applications.map((app) => (
            <div
              key={app.id}
              className="flex items-center justify-between p-4 hover:bg-muted/20 transition-colors"
            >
              <div className="flex items-center gap-3.5">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold text-sm">
                  {app.student?.full_name?.[0]?.toUpperCase() || "S"}
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-foreground">
                    {app.student?.full_name}
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    {app.student?.department} • GPA: <span className="font-medium text-foreground">{app.student?.gpa ?? "N/A"}</span>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-8">
                <div className="text-right hidden md:block">
                  <p className="text-xs font-semibold text-foreground max-w-44 truncate">
                    {app.internship?.title}
                  </p>
                  <p className="text-[11px] text-muted-foreground">
                    {app.internship?.company?.name}
                  </p>
                </div>

                <StatusBadge status={app.status} />

                <span className="text-xs text-muted-foreground hidden sm:inline">
                  {formatRelativeDate(app.created_at)}
                </span>

                <Button size="sm" asChild variant="outline" className="rounded-xl text-xs gap-1.5 h-8">
                  <Link href={`/student/applications/${app.id}`}>
                    <Eye className="size-3.5" /> Details
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
