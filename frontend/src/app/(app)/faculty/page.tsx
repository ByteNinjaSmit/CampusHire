"use client";

import Link from "next/link";
import { useAuth } from "@/providers/AuthProvider";
import { useDashboard } from "@/lib/api/hooks/reports";
import { useInternships } from "@/lib/api/hooks/internships";
import { useApplications } from "@/lib/api/hooks/applications";
import { useInterviews } from "@/lib/api/hooks/interviews";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatCard } from "@/components/shared/StatCard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ReportChartCard } from "@/components/shared/ReportViewer";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate, formatRelativeDate } from "@/lib/format";
import {
  Briefcase,
  Users,
  Clock,
  Calendar,
  PlusCircle,
  ArrowRight,
  Building2,
  FileCheck,
} from "lucide-react";

export default function FacultyDashboardPage() {
  const { user } = useAuth();
  const { data: dashboard, isLoading: isDashboardLoading } = useDashboard();
  const { data: internshipsData, isLoading: isInternshipsLoading } = useInternships({
    posted_by: user?.id,
    page_size: 5,
  });
  const { data: pendingAppsData } = useApplications({
    status: "PENDING",
    page_size: 5,
  });
  const { data: interviewsData } = useInterviews({
    page_size: 5,
  });

  const postings = internshipsData?.items ?? [];
  const pendingApps = pendingAppsData?.items ?? [];
  const interviews = interviewsData?.items ?? [];

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            Faculty Portal — {user?.full_name}
          </h1>
          <p className="text-sm text-muted-foreground">
            Manage your internship postings, review candidate applications, and schedule interviews.
          </p>
        </div>

        <Button asChild className="gap-2 rounded-xl">
          <Link href="/faculty/internships/new">
            <PlusCircle className="size-4" /> Create New Posting
          </Link>
        </Button>
      </div>

      {/* KPI Row */}
      {isDashboardLoading ? (
        <LoadingCardGrid count={4} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {dashboard?.kpis && dashboard.kpis.length > 0 ? (
            dashboard.kpis.map((k) => (
              <StatCard
                key={k.label}
                label={k.label}
                value={typeof k.value === "number" ? k.value : String(k.value)}
                format={k.format ?? "number"}
                delta={k.delta}
                hint={k.hint}
                icon={Briefcase}
              />
            ))
          ) : (
            <>
              <StatCard label="My Postings" value={internshipsData?.total ?? 0} icon={Briefcase} />
              <StatCard label="Pending Review" value={pendingAppsData?.total ?? 0} icon={Clock} />
              <StatCard label="Scheduled Interviews" value={interviews.length} icon={Calendar} />
              <StatCard label="Total Candidates" value={42} icon={Users} />
            </>
          )}
        </div>
      )}

      {/* Charts if available */}
      {dashboard?.charts && dashboard.charts.length > 0 && (
        <div className="grid gap-6 md:grid-cols-2">
          {dashboard.charts.map((c) => (
            <ReportChartCard key={c.id} chart={c} />
          ))}
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main 2 Cols: Applications Needing Review & Active Postings */}
        <div className="space-y-6 lg:col-span-2">
          {/* Applications Pending Review */}
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-lg">Candidates Needing Review</CardTitle>
                <CardDescription>Recently submitted applications awaiting initial review.</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              {pendingApps.length === 0 ? (
                <EmptyState
                  icon={FileCheck}
                  title="No pending reviews"
                  description="You are caught up on candidate submissions for your postings."
                />
              ) : (
                <div className="divide-y divide-border/60 rounded-xl border border-border/60">
                  {pendingApps.map((app) => (
                    <div
                      key={app.id}
                      className="flex flex-col gap-3 p-4 transition-colors hover:bg-muted/30 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-sm text-foreground">
                            {app.student?.full_name || "Applicant"}
                          </span>
                          <StatusBadge status={app.status} />
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {app.internship?.title} • Applied {formatRelativeDate(app.created_at)}
                        </p>
                      </div>

                      <Button size="sm" asChild variant="default" className="rounded-xl text-xs gap-1">
                        <Link href={`/faculty/review/${app.internship_id}`}>
                          Review Candidate <ArrowRight className="size-3.5" />
                        </Link>
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* My Postings Overview */}
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-lg">My Internship Postings</CardTitle>
                <CardDescription>Track applications and review candidates per role.</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild className="text-xs hover:text-primary">
                <Link href="/faculty/internships">View all postings</Link>
              </Button>
            </CardHeader>
            <CardContent>
              {isInternshipsLoading ? (
                <div className="space-y-3">
                  <div className="h-16 animate-pulse rounded-xl bg-muted" />
                  <div className="h-16 animate-pulse rounded-xl bg-muted" />
                </div>
              ) : postings.length === 0 ? (
                <EmptyState
                  icon={Briefcase}
                  title="No postings created"
                  description="Create an internship posting to begin receiving student applications."
                  action={
                    <Button asChild size="sm" className="rounded-xl">
                      <Link href="/faculty/internships/new">Create Posting</Link>
                    </Button>
                  }
                />
              ) : (
                <div className="divide-y divide-border/60 rounded-xl border border-border/60">
                  {postings.map((item) => (
                    <div
                      key={item.id}
                      className="flex flex-col gap-3 p-4 transition-colors hover:bg-muted/30 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-sm text-foreground">{item.title}</span>
                          <StatusBadge status={item.status} />
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {item.company?.name || "Campus Placement"} • Deadline: {formatDate(item.application_deadline)}
                        </p>
                      </div>

                      <div className="flex items-center gap-2 self-start sm:self-center">
                        <Button size="sm" asChild variant="outline" className="rounded-xl text-xs">
                          <Link href={`/faculty/review/${item.id}`}>Review Applicants</Link>
                        </Button>
                        <Button size="sm" asChild variant="ghost" className="rounded-xl text-xs">
                          <Link href={`/faculty/internships/${item.id}/edit`}>Edit</Link>
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* 1 Col Sidebar: Upcoming Interviews & Quick Links */}
        <div className="space-y-6">
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-lg">Interviews</CardTitle>
                <CardDescription>Upcoming candidate sessions.</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild className="text-xs hover:text-primary">
                <Link href="/faculty/interviews">Manage</Link>
              </Button>
            </CardHeader>
            <CardContent>
              {interviews.length === 0 ? (
                <p className="text-xs text-muted-foreground py-4 text-center">
                  No upcoming interviews scheduled.
                </p>
              ) : (
                <div className="space-y-3">
                  {interviews.map((iv) => (
                    <div key={iv.id} className="rounded-xl border border-border/60 p-3 space-y-1.5 text-xs bg-card">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-foreground">
                          {iv.application?.student?.full_name || "Student"}
                        </span>
                        <Badge variant="outline" className="text-[10px]">
                          {iv.mode}
                        </Badge>
                      </div>
                      <p className="text-muted-foreground text-[11px]">
                        {iv.application?.internship?.title}
                      </p>
                      <div className="flex items-center gap-1.5 text-primary pt-1 font-medium">
                        <Clock className="size-3.5" />
                        <span>{formatDate(iv.scheduled_at)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" asChild className="w-full justify-start gap-2 rounded-xl text-xs">
                <Link href="/faculty/evaluations">
                  <FileCheck className="size-4 text-indigo-500" /> Evaluations & Rubrics
                </Link>
              </Button>
              <Button variant="outline" asChild className="w-full justify-start gap-2 rounded-xl text-xs">
                <Link href="/faculty/companies">
                  <Building2 className="size-4 text-primary" /> Corporate Partners
                </Link>
              </Button>
              <Button variant="outline" asChild className="w-full justify-start gap-2 rounded-xl text-xs">
                <Link href="/faculty/reports">
                  <Briefcase className="size-4 text-emerald-500" /> Department Reports
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
