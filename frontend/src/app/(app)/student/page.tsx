"use client";

import Link from "next/link";
import { useAuth } from "@/providers/AuthProvider";
import { useDashboard } from "@/lib/api/hooks/reports";
import { useMyStudentProfile } from "@/lib/api/hooks/students";
import { useApplications } from "@/lib/api/hooks/applications";
import { useInterviews } from "@/lib/api/hooks/interviews";
import { useInternships } from "@/lib/api/hooks/internships";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatCard } from "@/components/shared/StatCard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ReportChartCard } from "@/components/shared/ReportViewer";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { formatDate, formatRelativeDate } from "@/lib/format";
import {
  Briefcase,
  Calendar,
  CheckCircle2,
  Clock,
  Compass,
  FileText,
  GraduationCap,
  Sparkles,
  ArrowRight,
  Building2,
  AlertCircle,
  Video,
} from "lucide-react";

export default function StudentDashboardPage() {
  const { user } = useAuth();
  const { data: dashboard, isLoading: isDashboardLoading } = useDashboard();
  const { data: profile } = useMyStudentProfile();
  const { data: appsData, isLoading: isAppsLoading } = useApplications({ page_size: 5 });
  const { data: interviewsData } = useInterviews({ page_size: 5 });
  const { data: recommendedData } = useInternships({
    page_size: 4,
  });

  const applications = appsData?.items ?? [];
  const interviews = interviewsData?.items ?? [];
  const recommended = recommendedData?.items ?? [];

  // Compute profile completeness
  let completeness = 30; // base account
  if (profile?.department) completeness += 15;
  if (profile?.gpa) completeness += 15;
  if (profile?.skills && profile.skills.length > 0) completeness += 20;
  if (profile?.default_resume) completeness += 20;

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            Welcome back, {user?.full_name?.split(" ")[0]} 👋
          </h1>
          <p className="text-sm text-muted-foreground">
            Track your internship applications, interview dates, and matching opportunities.
          </p>
        </div>

        <Button asChild className="gap-2 rounded-xl">
          <Link href="/internships">
            <Compass className="size-4" /> Explore Internships
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
              <StatCard label="Applications" value={appsData?.total ?? 0} icon={Briefcase} />
              <StatCard
                label="Under Review"
                value={applications.filter((a) => a.status === "UNDER_REVIEW").length}
                icon={Clock}
              />
              <StatCard
                label="Interviews"
                value={interviews.filter((i) => i.status === "SCHEDULED").length}
                icon={Calendar}
              />
              <StatCard
                label="Offers Received"
                value={applications.filter((a) => a.status === "ACCEPTED").length}
                icon={CheckCircle2}
              />
            </>
          )}
        </div>
      )}

      {/* Profile Completeness Alert if < 100% */}
      {completeness < 100 && (
        <Card className="rounded-2xl border-primary/30 bg-primary/5 shadow-xs">
          <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Sparkles className="size-4 text-primary" />
                <h4 className="font-semibold text-sm">Profile Completeness: {completeness}%</h4>
              </div>
              <p className="text-xs text-muted-foreground">
                Complete your academic profile and attach a default resume to expedite recruiter verification.
              </p>
              <div className="w-64 pt-2">
                <Progress value={completeness} className="h-2 rounded-full" />
              </div>
            </div>
            <Button size="sm" asChild variant="outline" className="rounded-xl self-start sm:self-center">
              <Link href="/profile">Complete Profile</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Main Content Grid: Active Applications (2 col) + Upcoming Interviews & Quick Actions (1 col) */}
      <div className="grid gap-8 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {/* Active Applications */}
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-lg">Recent Applications</CardTitle>
                <CardDescription>Track status updates and recruitment stages.</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild className="text-xs hover:text-primary">
                <Link href="/student/applications">View all ({appsData?.total ?? 0})</Link>
              </Button>
            </CardHeader>
            <CardContent>
              {isAppsLoading ? (
                <div className="space-y-3">
                  <div className="h-16 animate-pulse rounded-xl bg-muted" />
                  <div className="h-16 animate-pulse rounded-xl bg-muted" />
                </div>
              ) : applications.length === 0 ? (
                <EmptyState
                  icon={Briefcase}
                  title="No applications yet"
                  description="Start exploring opportunities and apply to roles that match your career goals."
                  action={
                    <Button asChild size="sm" className="rounded-xl">
                      <Link href="/internships">Browse Internships</Link>
                    </Button>
                  }
                />
              ) : (
                <div className="divide-y divide-border/60 rounded-xl border border-border/60">
                  {applications.map((app) => (
                    <div
                      key={app.id}
                      className="flex flex-col gap-3 p-4 transition-colors hover:bg-muted/30 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-sm text-foreground">
                            {app.internship?.title || "Internship"}
                          </span>
                          <StatusBadge status={app.status} />
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {app.internship?.company_name || "Company"} • Applied {formatRelativeDate(app.created_at)}
                        </p>
                      </div>

                      <Button size="sm" variant="outline" asChild className="rounded-xl text-xs gap-1">
                        <Link href={`/student/applications/${app.id}`}>
                          Track Status <ArrowRight className="size-3.5" />
                        </Link>
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Charts if provided */}
          {dashboard?.charts && dashboard.charts.length > 0 && (
            <div className="grid gap-6">
              {dashboard.charts.map((c) => (
                <ReportChartCard key={c.id} chart={c} />
              ))}
            </div>
          )}

          {/* Recommended Internships */}
          {recommended.length > 0 && (
            <Card className="rounded-2xl border-border/60 shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <div>
                  <CardTitle className="text-lg">Recommended for You</CardTitle>
                  <CardDescription>Based on your department and academic interests.</CardDescription>
                </div>
                <Button variant="ghost" size="sm" asChild className="text-xs hover:text-primary">
                  <Link href="/internships">Explore all</Link>
                </Button>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 sm:grid-cols-2">
                  {recommended.map((item) => (
                    <div
                      key={item.id}
                      className="flex flex-col justify-between rounded-xl border border-border/60 p-4 transition-all hover:border-primary/40 hover:bg-muted/20"
                    >
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Building2 className="size-4 text-muted-foreground" />
                          <span className="text-xs font-semibold text-muted-foreground">
                            {item.company?.name}
                          </span>
                        </div>
                        <h4 className="font-semibold text-sm line-clamp-1 hover:text-primary">
                          <Link href={`/internships/${item.id}`}>{item.title}</Link>
                        </h4>
                        <div className="flex flex-wrap gap-1">
                          <Badge variant="secondary" className="text-[10px]">
                            {item.work_mode}
                          </Badge>
                          {item.stipend_monthly && (
                            <Badge variant="outline" className="text-[10px] text-emerald-600 border-emerald-500/20">
                              {item.stipend_monthly} / mo
                            </Badge>
                          )}
                        </div>
                      </div>

                      <div className="pt-3 flex justify-end">
                        <Button size="sm" variant="ghost" asChild className="text-xs gap-1">
                          <Link href={`/internships/${item.id}`}>
                            Apply <ArrowRight className="size-3" />
                          </Link>
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Sidebar: Upcoming Interviews */}
        <div className="space-y-6">
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-lg">Upcoming Interviews</CardTitle>
                <CardDescription>Your schedule & interview links.</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild className="text-xs hover:text-primary">
                <Link href="/student/interviews">Calendar</Link>
              </Button>
            </CardHeader>
            <CardContent>
              {interviews.length === 0 ? (
                <div className="py-6 text-center text-xs text-muted-foreground">
                  <Calendar className="mx-auto size-8 text-muted-foreground/60 mb-2" />
                  No upcoming interviews scheduled yet.
                </div>
              ) : (
                <div className="space-y-3">
                  {interviews.map((iv) => (
                    <div
                      key={iv.id}
                      className="rounded-xl border border-border/60 p-3.5 space-y-2 bg-card"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-xs text-foreground">
                          {iv.internship?.title || "Technical Interview"}
                        </span>
                        <Badge variant="secondary" className="text-[10px]">
                          {iv.mode}
                        </Badge>
                      </div>

                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <Clock className="size-3.5" />
                        <span>{formatDate(iv.scheduled_at)}</span>
                        <span>({iv.duration_minutes} min)</span>
                      </div>

                      {iv.meeting_link && (
                        <div className="pt-1">
                          <Button size="sm" variant="outline" asChild className="w-full text-xs gap-1 rounded-lg">
                            <a href={iv.meeting_link} target="_blank" rel="noopener noreferrer">
                              <Video className="size-3 text-indigo-500" /> Join Meeting
                            </a>
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Documents Quick Access */}
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" asChild className="w-full justify-start gap-2 rounded-xl text-xs">
                <Link href="/documents">
                  <FileText className="size-4 text-primary" /> Manage Resumes & Documents
                </Link>
              </Button>
              <Button variant="outline" asChild className="w-full justify-start gap-2 rounded-xl text-xs">
                <Link href="/student/saved">
                  <Sparkles className="size-4 text-amber-500" /> View Saved Internships
                </Link>
              </Button>
              <Button variant="outline" asChild className="w-full justify-start gap-2 rounded-xl text-xs">
                <Link href="/student/feedback">
                  <GraduationCap className="size-4 text-emerald-500" /> Submit Post-Internship Feedback
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
