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

export default function CompanyDashboardPage() {
  const { user } = useAuth();
  const { data: dashboard, isLoading: isDashboardLoading } = useDashboard();
  const { data: internshipsData, isLoading: isInternshipsLoading } = useInternships({ page_size: 5 });
  const { data: pendingAppsData } = useApplications({ status: "PENDING", page_size: 5 });
  const { data: interviewsData } = useInterviews({ page_size: 5 });

  const postings = internshipsData?.items ?? [];
  const pendingApps = pendingAppsData?.items ?? [];
  const interviews = interviewsData?.items ?? [];

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            Company Portal — {user?.full_name}
          </h1>
          <p className="text-sm text-muted-foreground">
            Manage your company&apos;s internship postings, review campus talent, and schedule interviews.
          </p>
        </div>

        <Button asChild className="gap-2 rounded-xl">
          <Link href="/company/internships/new">
            <PlusCircle className="size-4" /> Post New Internship
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
              <StatCard label="Active Postings" value={internshipsData?.total ?? 0} icon={Briefcase} />
              <StatCard label="Pending Applications" value={pendingAppsData?.total ?? 0} icon={Clock} />
              <StatCard label="Scheduled Interviews" value={interviews.length} icon={Calendar} />
              <StatCard label="Candidate Pipeline" value={35} icon={Users} />
            </>
          )}
        </div>
      )}

      {/* Charts */}
      {dashboard?.charts && dashboard.charts.length > 0 && (
        <div className="grid gap-6 md:grid-cols-2">
          {dashboard.charts.map((c) => (
            <ReportChartCard key={c.id} chart={c} />
          ))}
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Left 2 cols */}
        <div className="space-y-6 lg:col-span-2">
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-lg">Recent Applicant Submissions</CardTitle>
                <CardDescription>Candidates ready for resume review.</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              {pendingApps.length === 0 ? (
                <EmptyState
                  icon={FileCheck}
                  title="No pending applicants"
                  description="All submitted applications for your postings have been reviewed."
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
                        <Link href={`/company/review/${app.internship_id}`}>
                          Review Candidate <ArrowRight className="size-3.5" />
                        </Link>
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-lg">Company Internship Postings</CardTitle>
                <CardDescription>Active campus recruitment listings.</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild className="text-xs hover:text-primary">
                <Link href="/company/internships">Manage all postings</Link>
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
                  title="No postings yet"
                  description="Publish your first internship posting to begin receiving candidates."
                  action={
                    <Button asChild size="sm" className="rounded-xl">
                      <Link href="/company/internships/new">Create Posting</Link>
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
                          {item.location} • Deadline: {formatDate(item.application_deadline)}
                        </p>
                      </div>

                      <div className="flex items-center gap-2 self-start sm:self-center">
                        <Button size="sm" asChild variant="outline" className="rounded-xl text-xs">
                          <Link href={`/company/review/${item.id}`}>Review</Link>
                        </Button>
                        <Button size="sm" asChild variant="ghost" className="rounded-xl text-xs">
                          <Link href={`/company/internships/${item.id}/edit`}>Edit</Link>
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Upcoming Interviews</CardTitle>
              <CardDescription>Scheduled interview panels.</CardDescription>
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
                          {iv.application?.student?.full_name || "Candidate"}
                        </span>
                        <span className="text-[10px] text-muted-foreground">{iv.mode}</span>
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
              <CardTitle className="text-lg">Quick Shortcuts</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" asChild className="w-full justify-start gap-2 rounded-xl text-xs">
                <Link href="/company/profile">
                  <Building2 className="size-4 text-primary" /> Update Company Profile
                </Link>
              </Button>
              <Button variant="outline" asChild className="w-full justify-start gap-2 rounded-xl text-xs">
                <Link href="/company/evaluations">
                  <FileCheck className="size-4 text-indigo-500" /> Evaluations & Scores
                </Link>
              </Button>
              <Button variant="outline" asChild className="w-full justify-start gap-2 rounded-xl text-xs">
                <Link href="/company/reports">
                  <Briefcase className="size-4 text-emerald-500" /> Recruitment Reports
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
