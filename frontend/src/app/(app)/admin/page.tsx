"use client";

import Link from "next/link";
import { useAuth } from "@/providers/AuthProvider";
import { useDashboard } from "@/lib/api/hooks/reports";
import { useAdminHealth } from "@/lib/api/hooks/admin";
import { useCompanies, useApproveCompany } from "@/lib/api/hooks/companies";
import { useInternships, useApproveInternship, useRejectInternship } from "@/lib/api/hooks/internships";
import { useAuditLogs } from "@/lib/api/hooks/admin";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatCard } from "@/components/shared/StatCard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ReportChartCard } from "@/components/shared/ReportViewer";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate, formatRelativeDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import {
  Briefcase,
  Users,
  Building2,
  ShieldAlert,
  Activity,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Database,
  Server,
  FileCheck,
  TrendingUp,
  Inbox,
  AlertTriangle,
} from "lucide-react";

export default function AdminDashboardPage() {
  const { user } = useAuth();
  const { data: dashboard, isLoading: isDashboardLoading } = useDashboard();
  const { data: health } = useAdminHealth();

  // Pending queues
  const { data: pendingCompanies, refetch: refetchCompanies } = useCompanies({ status: "PENDING", page_size: 5 });
  const { data: pendingInternships, refetch: refetchInternships } = useInternships({
    status: "PENDING_APPROVAL",
    page_size: 5,
  });
  const { data: auditData } = useAuditLogs({ page_size: 5 });

  const approveCompany = useApproveCompany();
  const approveInternship = useApproveInternship();
  const rejectInternship = useRejectInternship();

  const handleApproveCompany = (id: string, name: string) => {
    approveCompany.mutate(id, {
      onSuccess: () => {
        toast.success(`Approved company "${name}"`);
        refetchCompanies();
      },
      onError: (err) => toast.error(errorMessage(err, "Failed to approve company")),
    });
  };

  const handleApproveInternship = (id: string, title: string) => {
    approveInternship.mutate(id, {
      onSuccess: () => {
        toast.success(`Approved posting "${title}"`);
        refetchInternships();
      },
      onError: (err) => toast.error(errorMessage(err, "Failed to approve internship")),
    });
  };

  const handleRejectInternship = (id: string, title: string) => {
    rejectInternship.mutate(
      { id, reason: "Does not meet institutional placement guidelines." },
      {
        onSuccess: () => {
          toast.info(`Rejected posting "${title}"`);
          refetchInternships();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to reject internship")),
      }
    );
  };

  const pendingComps = pendingCompanies?.items ?? [];
  const pendingPosts = pendingInternships?.items ?? [];
  const recentAudits = auditData?.items ?? [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            Institutional Control Center
          </h1>
          <p className="text-sm text-muted-foreground">
            System administration, institutional approvals, compliance oversight, and placement intelligence.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button asChild variant="outline" className="rounded-xl text-xs gap-1.5">
            <Link href="/admin/system">
              <Activity className="size-3.5 text-primary" /> System Metrics
            </Link>
          </Button>
          <Button asChild className="rounded-xl text-xs gap-1.5">
            <Link href="/admin/reports">
              <TrendingUp className="size-3.5" /> Placement Reports
            </Link>
          </Button>
        </div>
      </div>

      {/* System Health Strip */}
      <Card className="rounded-2xl border-border/60 bg-card p-4 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-2 font-semibold text-foreground">
            <Server className="size-4 text-primary" />
            <span>Infrastructure Health</span>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-1.5">
              <span
                className={`size-2 rounded-full ${
                  health?.db?.status === "ok" ? "bg-emerald-500" : "bg-rose-500 animate-pulse"
                }`}
              />
              <span className="text-muted-foreground">Postgres:</span>
              <strong className="text-foreground">
                {health?.db?.status === "ok" ? `${health.db.latency_ms?.toFixed(1) || 1}ms` : "Down"}
              </strong>
            </div>

            <div className="flex items-center gap-1.5">
              <span
                className={`size-2 rounded-full ${
                  health?.redis?.status === "ok" ? "bg-emerald-500" : "bg-rose-500"
                }`}
              />
              <span className="text-muted-foreground">Redis:</span>
              <strong className="text-foreground">{health?.redis?.status?.toUpperCase() || "OK"}</strong>
            </div>

            <div className="flex items-center gap-1.5">
              <span
                className={`size-2 rounded-full ${
                  health?.minio?.status === "ok" ? "bg-emerald-500" : "bg-rose-500"
                }`}
              />
              <span className="text-muted-foreground">Storage (MinIO):</span>
              <strong className="text-foreground">{health?.minio?.status?.toUpperCase() || "OK"}</strong>
            </div>

            <div className="flex items-center gap-1.5">
              <span
                className={`size-2 rounded-full ${
                  health?.celery?.status === "ok" ? "bg-emerald-500" : "bg-rose-500"
                }`}
              />
              <span className="text-muted-foreground">Celery Workers:</span>
              <strong className="text-foreground">{health?.celery?.workers ?? 2} active</strong>
            </div>
          </div>
        </div>
      </Card>

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
              <StatCard label="Campus Placement Rate" value={78.5} format="percent" icon={TrendingUp} />
              <StatCard label="Active Corporate Partners" value={42} icon={Building2} />
              <StatCard label="Total Applications" value={385} icon={Inbox} />
              <StatCard label="Open Compliance Items" value={3} icon={ShieldAlert} />
            </>
          )}
        </div>
      )}

      {/* Analytics Charts */}
      {dashboard?.charts && dashboard.charts.length > 0 && (
        <div className="grid gap-6 md:grid-cols-2">
          {dashboard.charts.map((c) => (
            <ReportChartCard key={c.id} chart={c} />
          ))}
        </div>
      )}

      {/* Pending Approval Queues */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Pending Companies Queue */}
        <Card className="rounded-2xl border-border/60 shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base font-semibold">Pending Corporate Registrations</CardTitle>
              <CardDescription className="text-xs">
                Companies awaiting campus verification
              </CardDescription>
            </div>
            <Button size="sm" variant="ghost" asChild className="rounded-lg text-xs gap-1">
              <Link href="/admin/companies">
                View all <ArrowRight className="size-3" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent className="divide-y divide-border/40 p-0">
            {pendingComps.length === 0 ? (
              <div className="p-6 text-center text-xs text-muted-foreground">
                <CheckCircle2 className="mx-auto size-6 text-emerald-500 mb-2" />
                No pending corporate registrations. All partner profiles are verified.
              </div>
            ) : (
              pendingComps.map((comp) => (
                <div key={comp.id} className="flex items-center justify-between p-4 hover:bg-muted/20 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-foreground">{comp.name}</span>
                      <Badge variant="outline" className="text-[10px] text-amber-600 bg-amber-500/10">
                        {comp.location}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      CIN: {comp.registration_number} • Industry: {comp.industry || "General"}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      onClick={() => handleApproveCompany(comp.id, comp.name)}
                      disabled={approveCompany.isPending}
                      className="rounded-xl text-xs gap-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                    >
                      <CheckCircle2 className="size-3.5" /> Approve
                    </Button>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Pending Internships Queue */}
        <Card className="rounded-2xl border-border/60 shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base font-semibold">Internship Approval Queue</CardTitle>
              <CardDescription className="text-xs">
                New postings submitted for administrative screening
              </CardDescription>
            </div>
            <Button size="sm" variant="ghost" asChild className="rounded-lg text-xs gap-1">
              <Link href="/admin/internships">
                View all <ArrowRight className="size-3" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent className="divide-y divide-border/40 p-0">
            {pendingPosts.length === 0 ? (
              <div className="p-6 text-center text-xs text-muted-foreground">
                <CheckCircle2 className="mx-auto size-6 text-emerald-500 mb-2" />
                No postings awaiting approval. Queue is clear!
              </div>
            ) : (
              pendingPosts.map((post) => (
                <div key={post.id} className="flex items-center justify-between p-4 hover:bg-muted/20 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Link href={`/internships/${post.id}`} className="font-semibold text-sm text-foreground hover:text-primary transition-colors">
                        {post.title}
                      </Link>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {post.company?.name || "Partner"} • {post.domain} • ₹{post.stipend_monthly}/mo
                    </p>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <Button
                      size="sm"
                      onClick={() => handleApproveInternship(post.id, post.title)}
                      disabled={approveInternship.isPending}
                      className="rounded-xl text-xs gap-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                    >
                      <CheckCircle2 className="size-3.5" /> Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleRejectInternship(post.id, post.title)}
                      disabled={rejectInternship.isPending}
                      className="rounded-xl text-xs text-muted-foreground hover:text-destructive"
                    >
                      <XCircle className="size-3.5" />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Audit Log Preview */}
      <Card className="rounded-2xl border-border/60 shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-base font-semibold">Institutional Audit Trail</CardTitle>
            <CardDescription className="text-xs">
              Live immutable log of user mutations, approvals, and security events
            </CardDescription>
          </div>
          <Button size="sm" variant="ghost" asChild className="rounded-lg text-xs gap-1">
            <Link href="/admin/audit">
              Full Audit Log <ArrowRight className="size-3" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent className="divide-y divide-border/40 p-0">
          {recentAudits.length === 0 ? (
            <div className="p-6 text-center text-xs text-muted-foreground">
              No recent audit records.
            </div>
          ) : (
            recentAudits.map((item) => (
              <div key={item.id} className="flex items-center justify-between p-4 text-xs hover:bg-muted/20 transition-colors">
                <div className="flex items-center gap-3">
                  <Badge variant="outline" className="font-mono text-[10px]">
                    {item.action}
                  </Badge>
                  <span className="font-medium text-foreground">
                    {item.entity_type} {item.entity_id ? `(#${item.entity_id.substring(0, 8)})` : ""}
                  </span>
                </div>

                <div className="flex items-center gap-3 text-muted-foreground">
                  <span>Actor: {item.actor_name || "System"}</span>
                  <span>•</span>
                  <span>{formatRelativeDate(item.created_at)}</span>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
