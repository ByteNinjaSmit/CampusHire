"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useApplication, useWithdrawApplication } from "@/lib/api/hooks/applications";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ApplicationTimeline } from "@/components/shared/ApplicationTimeline";
import { PdfViewer } from "@/components/shared/PdfViewer";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { ErrorState } from "@/components/shared/ErrorState";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate, formatRelativeDate, formatCurrency } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import {
  Briefcase,
  Building2,
  Calendar,
  Clock,
  FileText,
  ArrowLeft,
  XCircle,
  Video,
  CheckCircle2,
  Award,
  ExternalLink,
} from "lucide-react";

export default function StudentApplicationDetailPage() {
  const params = useParams();
  const id = typeof params?.id === "string" ? params.id : "";
  const router = useRouter();

  const { data: application, isLoading, error, refetch } = useApplication(id);
  const withdrawApp = useWithdrawApplication();
  const [showWithdraw, setShowWithdraw] = useState(false);

  if (isLoading) {
    return <LoadingCardGrid count={2} />;
  }

  if (error || !application) {
    return (
      <ErrorState
        title="Application not found"
        description="The application you requested could not be retrieved."
        onRetry={() => refetch()}
      />
    );
  }

  const isWithdrawable = ["PENDING", "UNDER_REVIEW", "SHORTLISTED", "INTERVIEW"].includes(application.status);

  const handleWithdraw = () => {
    withdrawApp.mutate(
      { id: application.id, reason: "Withdrawn by candidate" },
      {
        onSuccess: () => {
          toast.success("Application successfully withdrawn");
          setShowWithdraw(false);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to withdraw application")),
      }
    );
  };

  const internship = application.internship;
  const answers = (application.answers || {}) as Record<string, unknown>;

  return (
    <div className="space-y-8">
      <div>
        <Link
          href="/student/applications"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-3 transition-colors"
        >
          <ArrowLeft className="size-3.5" /> Back to applications
        </Link>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                {internship?.title || "Application"}
              </h1>
              <StatusBadge status={application.status} />
            </div>
            <p className="text-sm text-muted-foreground">
              {internship?.company?.name} • Submitted {formatDate(application.created_at)}
            </p>
          </div>

          {isWithdrawable && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowWithdraw(true)}
              className="rounded-xl text-rose-600 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/30 gap-1.5 self-start"
            >
              <XCircle className="size-4" /> Withdraw Application
            </Button>
          )}
        </div>
      </div>

      {/* Offer Received Alert if ACCEPTED */}
      {application.status === "ACCEPTED" && (
        <Card className="rounded-2xl border-emerald-500/30 bg-emerald-500/5 shadow-xs">
          <CardContent className="flex items-start gap-4 p-5">
            <Award className="size-8 text-emerald-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h3 className="font-semibold text-base text-foreground">Congratulations on Your Offer!</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Your application has been accepted for this internship position. Check your email for formal onboarding
                documents and follow-up communication from the hiring team.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Left Content (2 cols) */}
        <div className="space-y-6 lg:col-span-2">
          {/* Status Timeline */}
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">Application Progress</CardTitle>
              <CardDescription>Chronological updates from recruiters and faculty.</CardDescription>
            </CardHeader>
            <CardContent>
              <ApplicationTimeline events={application.timeline || []} />
            </CardContent>
          </Card>

          {/* Submitted Cover Letter & Answers */}
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">Submitted Application Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="space-y-1.5">
                <span className="text-xs font-semibold uppercase text-muted-foreground">Cover Letter</span>
                <p className="rounded-xl bg-muted/30 p-4 leading-relaxed whitespace-pre-line text-foreground/90">
                  {application.cover_letter || "None provided"}
                </p>
              </div>

              {answers.summary && (
                <div className="space-y-1.5">
                  <span className="text-xs font-semibold uppercase text-muted-foreground">Qualifications Summary</span>
                  <p className="text-foreground/90">{answers.summary}</p>
                </div>
              )}

              {answers.skills && Array.isArray(answers.skills) && answers.skills.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-xs font-semibold uppercase text-muted-foreground">Highlighted Skills</span>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {answers.skills.map((s: string) => (
                      <Badge key={s} variant="secondary" className="text-xs">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {answers.relevant_coursework && (
                <div className="space-y-1.5">
                  <span className="text-xs font-semibold uppercase text-muted-foreground">Relevant Coursework</span>
                  <p className="text-foreground/90">{answers.relevant_coursework}</p>
                </div>
              )}

              {answers.portfolio_url && (
                <div className="space-y-1.5">
                  <span className="text-xs font-semibold uppercase text-muted-foreground">Portfolio Link</span>
                  <div>
                    <a
                      href={answers.portfolio_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-primary hover:underline text-xs"
                    >
                      {answers.portfolio_url} <ExternalLink className="size-3" />
                    </a>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Submitted Resume Preview */}
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">Attached Resume</CardTitle>
              <CardDescription>PDF resume submitted with this candidate profile.</CardDescription>
            </CardHeader>
            <CardContent>
              <PdfViewer applicationId={application.id} height={500} />
            </CardContent>
          </Card>
        </div>

        {/* Sidebar: Interviews & Role Info (1 col) */}
        <div className="space-y-6">
          {/* Scheduled Interviews */}
          <Card className="rounded-2xl border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">Interviews</CardTitle>
              <CardDescription>Scheduled rounds for this application.</CardDescription>
            </CardHeader>
            <CardContent>
              {!application.interviews || application.interviews.length === 0 ? (
                <p className="text-xs text-muted-foreground py-2">
                  No interview scheduled yet. You will be notified as soon as an interview slot is confirmed.
                </p>
              ) : (
                <div className="space-y-3">
                  {application.interviews.map((iv) => (
                    <div
                      key={iv.id}
                      className="rounded-xl border border-border/60 p-3.5 space-y-2 bg-card"
                    >
                      <div className="flex items-center justify-between">
                        <Badge variant="outline" className="text-xs font-semibold">
                          Round {iv.round || 1} • {iv.mode}
                        </Badge>
                        <Badge variant="secondary" className="text-[10px]">
                          {iv.status}
                        </Badge>
                      </div>

                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <Clock className="size-3.5" />
                        <span>{formatDate(iv.scheduled_at)}</span>
                        <span>({iv.duration_minutes} min)</span>
                      </div>

                      {iv.meeting_link && (
                        <div className="pt-2">
                          <Button size="sm" asChild variant="default" className="w-full gap-1.5 rounded-xl text-xs">
                            <a href={iv.meeting_link} target="_blank" rel="noopener noreferrer">
                              <Video className="size-3.5" /> Join Video Meeting
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

          {/* Shared Evaluations */}
          {application.evaluations && application.evaluations.length > 0 && (
            <Card className="rounded-2xl border-border/60 shadow-sm">
              <CardHeader>
                <CardTitle className="text-lg">Evaluator Feedback</CardTitle>
                <CardDescription>Shared interview feedback & evaluation scores.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {application.evaluations.map((ev) => (
                  <div key={ev.id} className="rounded-xl border border-border/60 p-3.5 space-y-2 bg-muted/20">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-foreground">{ev.form_name || "Evaluation"}</span>
                      <span className="font-bold text-sm text-primary">{ev.weighted_score}%</span>
                    </div>
                    {ev.overall_comments && (
                      <p className="text-xs text-muted-foreground leading-relaxed italic">
                        &ldquo;{ev.overall_comments}&rdquo;
                      </p>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Quick Internship Summary */}
          {internship && (
            <Card className="rounded-2xl border-border/60 shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Internship Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2.5 text-xs text-muted-foreground">
                <div className="flex justify-between">
                  <span>Work Mode</span>
                  <span className="font-medium text-foreground">{internship.work_mode}</span>
                </div>
                <div className="flex justify-between">
                  <span>Duration</span>
                  <span className="font-medium text-foreground">{internship.duration_weeks} Weeks</span>
                </div>
                <div className="flex justify-between">
                  <span>Monthly Stipend</span>
                  <span className="font-medium text-foreground">
                    {internship.stipend_monthly ? `${formatCurrency(internship.stipend_monthly)}` : "Unpaid"}
                  </span>
                </div>
                <div className="pt-2">
                  <Button variant="outline" size="sm" asChild className="w-full rounded-xl text-xs">
                    <Link href={`/internships/${internship.id}`}>View Original Posting</Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={showWithdraw}
        onOpenChange={setShowWithdraw}
        title="Withdraw Application"
        description="Are you sure you want to withdraw your application? This action cannot be reversed."
        confirmText="Withdraw"
        variant="destructive"
        onConfirm={handleWithdraw}
      />
    </div>
  );
}
