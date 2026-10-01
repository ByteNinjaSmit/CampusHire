"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useInternship, useInternshipApplications } from "@/lib/api/hooks/internships";
import {
  useUpdateApplicationStatus,
  useWithdrawApplication,
} from "@/lib/api/hooks/applications";
import { useCreateInterview } from "@/lib/api/hooks/interviews";
import { useEvaluationForms, useCreateEvaluation } from "@/lib/api/hooks/evaluations";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ApplicationTimeline } from "@/components/shared/ApplicationTimeline";
import { PdfViewer } from "@/components/shared/PdfViewer";
import { ScoreSlider } from "@/components/shared/ScoreSlider";
import { SearchInput } from "@/components/shared/SearchInput";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { formatDate, formatRelativeDate, formatCurrency } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import type { Application, ApplicationStatus, InterviewMode, EvaluationRecommendation } from "@/lib/api/types";
import {
  Users,
  CheckCircle2,
  XCircle,
  Clock,
  Calendar,
  FileText,
  Mail,
  Phone,
  GraduationCap,
  ExternalLink,
  Award,
  Video,
  ArrowLeft,
  Filter,
} from "lucide-react";

export default function CandidateReviewPage() {
  const params = useParams();
  const internshipId = typeof params?.internshipId === "string" ? params.internshipId : "";

  const { data: internship, isLoading: isInternshipLoading } = useInternship(internshipId);
  const { data: appsData, isLoading: isAppsLoading, refetch } = useInternshipApplications(internshipId, {
    page: 1,
    page_size: 100,
  });

  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [search, setSearch] = useState("");

  // Action Dialog States
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [evalOpen, setEvalOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [offerOpen, setOfferOpen] = useState(false);

  // Form states for Interview Scheduling
  const [interviewMode, setInterviewMode] = useState<InterviewMode>("ONLINE");
  const [scheduledAt, setScheduledAt] = useState("");
  const [durationMin, setDurationMin] = useState(45);
  const [meetingLink, setMeetingLink] = useState("");
  const [interviewerName, setInterviewerName] = useState("");

  // Form states for Evaluation
  const { data: forms } = useEvaluationForms();
  const defaultForm = forms?.[0];
  const [scores, setScores] = useState<Record<string, number>>({});
  const [evalRecommendation, setEvalRecommendation] = useState<EvaluationRecommendation>("YES");
  const [evalComments, setEvalComments] = useState("");

  // Reject / Offer states
  const [rejectReason, setRejectReason] = useState("");
  const [offerStipend, setOfferStipend] = useState<number | string>(internship?.stipend_monthly || "");
  const [offerStartDate, setOfferStartDate] = useState(internship?.start_date ? internship.start_date.substring(0, 10) : "");

  const updateStatus = useUpdateApplicationStatus();
  const createInterview = useCreateInterview();
  const createEvaluation = useCreateEvaluation();

  const applications = (appsData?.items ?? []).filter((app) => {
    if (statusFilter !== "ALL" && app.status !== statusFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        app.student?.full_name?.toLowerCase().includes(q) ||
        app.student?.department?.toLowerCase().includes(q) ||
        app.student?.enrollment_no?.toLowerCase().includes(q)
      );
    }
    return true;
  });

  // Auto-select first application
  const activeApp = applications.find((a) => a.id === selectedAppId) || applications[0];

  const handleUpdateStatus = (newStatus: ApplicationStatus, note?: string) => {
    if (!activeApp) return;
    updateStatus.mutate(
      { id: activeApp.id, body: { status: newStatus, note } },
      {
        onSuccess: () => {
          toast.success(`Application updated to ${newStatus.replace("_", " ")}`);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to update status")),
      }
    );
  };

  const handleScheduleInterview = (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeApp || !scheduledAt) {
      toast.error("Please pick a scheduled interview time.");
      return;
    }

    createInterview.mutate(
      {
        application_id: activeApp.id,
        scheduled_at: scheduledAt.includes("Z") ? scheduledAt : `${scheduledAt}:00Z`,
        duration_minutes: Number(durationMin) || 45,
        mode: interviewMode,
        meeting_link: meetingLink || undefined,
        interviewer_name: interviewerName || "Faculty Hiring Committee",
      },
      {
        onSuccess: () => {
          toast.success("Interview scheduled. Candidate has been notified.");
          setScheduleOpen(false);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to schedule interview")),
      }
    );
  };

  const handleScoreChange = (critId: string, val: number) => {
    setScores((prev) => ({ ...prev, [critId]: val }));
  };

  // Compute live weighted score
  const computeLiveScore = () => {
    if (!defaultForm || !defaultForm.criteria || defaultForm.criteria.length === 0) return 0;
    let sumWeight = 0;
    let weightedSum = 0;
    for (const c of defaultForm.criteria) {
      const score = scores[c.id] ?? 0;
      const w = c.weight ?? 1;
      sumWeight += w;
      weightedSum += (score / (c.max_score || 10)) * w;
    }
    return sumWeight > 0 ? Math.round((weightedSum / sumWeight) * 100) : 0;
  };

  const handleSubmitEvaluation = (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeApp || !defaultForm) return;

    const formattedScores = (defaultForm.criteria || []).map((c) => ({
      criterion_id: c.id,
      score: scores[c.id] ?? 5,
    }));

    createEvaluation.mutate(
      {
        application_id: activeApp.id,
        form_id: defaultForm.id,
        scores: formattedScores,
        recommendation: evalRecommendation,
        overall_comments: evalComments.trim() || "Candidate evaluated",
        shared_with_student: true,
      },
      {
        onSuccess: () => {
          toast.success("Evaluation submitted and shared with student.");
          setEvalOpen(false);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to record evaluation")),
      }
    );
  };

  if (isInternshipLoading || isAppsLoading) {
    return <LoadingCardGrid count={2} />;
  }

  const answers = (activeApp?.answers || {}) as Record<string, unknown>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <Link
          href="/faculty/internships"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="size-3.5" /> Back to My Postings
        </Link>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <PageHeader
            title={`Candidate Review: ${internship?.title || "Posting"}`}
            description={`${appsData?.total ?? 0} total applicants • Review resumes, schedule interviews, and submit ratings.`}
          />
        </div>
      </div>

      {/* Split Screen Layout */}
      <div className="grid gap-6 lg:grid-cols-12 min-h-[700px]">
        {/* Left: Applicant List (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="rounded-2xl border border-border/60 bg-card p-4 shadow-sm space-y-3">
            <SearchInput value={search} onChange={setSearch} placeholder="Filter applicants..." />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="h-9 rounded-xl text-xs">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent className="rounded-xl">
                <SelectItem value="ALL">All Applicants ({appsData?.total ?? 0})</SelectItem>
                <SelectItem value="PENDING">Pending Review</SelectItem>
                <SelectItem value="UNDER_REVIEW">Under Review</SelectItem>
                <SelectItem value="SHORTLISTED">Shortlisted</SelectItem>
                <SelectItem value="INTERVIEW">Interview Stage</SelectItem>
                <SelectItem value="ACCEPTED">Accepted</SelectItem>
                <SelectItem value="REJECTED">Rejected</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="divide-y divide-border/60 rounded-2xl border border-border/60 bg-card shadow-sm max-h-[640px] overflow-y-auto">
            {applications.length === 0 ? (
              <div className="p-8 text-center text-xs text-muted-foreground">
                No candidates match the filter criteria.
              </div>
            ) : (
              applications.map((app) => {
                const isSelected = activeApp?.id === app.id;
                return (
                  <div
                    key={app.id}
                    onClick={() => setSelectedAppId(app.id)}
                    className={`cursor-pointer p-4 transition-colors ${
                      isSelected
                        ? "bg-primary/10 border-l-4 border-l-primary"
                        : "hover:bg-muted/40"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="font-semibold text-sm text-foreground">
                          {app.student?.full_name || "Applicant"}
                        </h4>
                        <p className="text-xs text-muted-foreground">
                          {app.student?.department} • GPA: {app.student?.gpa ?? "N/A"}
                        </p>
                      </div>
                      <StatusBadge status={app.status} />
                    </div>
                    <div className="mt-2 flex items-center justify-between text-[11px] text-muted-foreground">
                      <span>Applied {formatRelativeDate(app.created_at)}</span>
                      {app.interviews && app.interviews.length > 0 && (
                        <span className="text-primary font-medium">Interview set</span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right: Candidate Detail Panel (8 cols) */}
        <div className="lg:col-span-8">
          {!activeApp ? (
            <EmptyState
              icon={Users}
              title="No candidate selected"
              description="Select a candidate from the left list to review their resume and profile."
            />
          ) : (
            <Card className="rounded-2xl border-border/60 shadow-sm">
              <CardContent className="space-y-6 p-6">
                {/* Candidate Header & Top Action Bar */}
                <div className="flex flex-col gap-4 border-b pb-5 sm:flex-row sm:items-start sm:justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h2 className="text-xl font-bold text-foreground">
                        {activeApp.student?.full_name}
                      </h2>
                      <StatusBadge status={activeApp.status} />
                    </div>
                    <p className="text-xs text-muted-foreground flex flex-wrap items-center gap-2">
                      <span>{activeApp.student?.department}</span>
                      <span>•</span>
                      <span>Enrollment: {activeApp.student?.enrollment_no || "N/A"}</span>
                      <span>•</span>
                      <span className="font-semibold text-foreground">
                        GPA: {activeApp.student?.gpa ?? "N/A"} / 4.00
                      </span>
                    </p>
                  </div>

                  {/* Actions Row */}
                  <div className="flex flex-wrap items-center gap-2">
                    {activeApp.status === "PENDING" && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleUpdateStatus("UNDER_REVIEW")}
                        className="rounded-xl text-xs"
                      >
                        Start Review
                      </Button>
                    )}

                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleUpdateStatus("SHORTLISTED")}
                      className="rounded-xl text-xs gap-1 text-indigo-600 hover:text-indigo-700"
                    >
                      <CheckCircle2 className="size-3.5" /> Shortlist
                    </Button>

                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setScheduleOpen(true)}
                      className="rounded-xl text-xs gap-1 text-amber-600 hover:text-amber-700"
                    >
                      <Calendar className="size-3.5" /> Schedule Interview
                    </Button>

                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setEvalOpen(true)}
                      className="rounded-xl text-xs gap-1 text-primary hover:text-primary"
                    >
                      <Award className="size-3.5" /> Evaluate
                    </Button>

                    <Button
                      size="sm"
                      variant="default"
                      onClick={() => setOfferOpen(true)}
                      className="rounded-xl text-xs gap-1 bg-emerald-600 hover:bg-emerald-700"
                    >
                      Accept / Offer
                    </Button>

                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setRejectOpen(true)}
                      className="rounded-xl text-xs text-rose-600 hover:text-rose-700"
                    >
                      Reject
                    </Button>
                  </div>
                </div>

                {/* Candidate Review Tabs */}
                <Tabs defaultValue="resume" className="space-y-4">
                  <TabsList className="bg-muted/60">
                    <TabsTrigger value="resume" className="gap-1.5">
                      <FileText className="size-3.5" /> Resume PDF
                    </TabsTrigger>
                    <TabsTrigger value="overview">Overview & Cover Letter</TabsTrigger>
                    <TabsTrigger value="timeline">Timeline & History</TabsTrigger>
                  </TabsList>

                  {/* Resume PDF Tab */}
                  <TabsContent value="resume" className="space-y-4">
                    <PdfViewer applicationId={activeApp.id} height={550} />
                  </TabsContent>

                  {/* Overview Tab */}
                  <TabsContent value="overview" className="space-y-5 text-sm">
                    <div className="space-y-1.5">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        Candidate Cover Letter
                      </h4>
                      <p className="rounded-xl bg-muted/30 p-4 leading-relaxed whitespace-pre-line text-foreground/90">
                        {activeApp.cover_letter || "No cover letter provided."}
                      </p>
                    </div>

                    {answers.summary && (
                      <div className="space-y-1.5">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                          Qualifications Summary
                        </h4>
                        <p className="text-foreground/90">{answers.summary}</p>
                      </div>
                    )}

                    {answers.skills && Array.isArray(answers.skills) && answers.skills.length > 0 && (
                      <div className="space-y-1.5">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                          Skills
                        </h4>
                        <div className="flex flex-wrap gap-1.5">
                          {answers.skills.map((s: string) => (
                            <Badge key={s} variant="secondary">
                              {s}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {answers.relevant_coursework && (
                      <div className="space-y-1.5">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                          Relevant Coursework
                        </h4>
                        <p className="text-foreground/90">{answers.relevant_coursework}</p>
                      </div>
                    )}

                    {answers.portfolio_url && (
                      <div className="space-y-1.5">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                          Portfolio Link
                        </h4>
                        <a
                          href={answers.portfolio_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-primary hover:underline text-xs"
                        >
                          {answers.portfolio_url} <ExternalLink className="size-3" />
                        </a>
                      </div>
                    )}
                  </TabsContent>

                  {/* Timeline Tab */}
                  <TabsContent value="timeline" className="space-y-4">
                    <ApplicationTimeline events={activeApp.timeline || []} />
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Schedule Interview Dialog */}
      <Dialog open={scheduleOpen} onOpenChange={setScheduleOpen}>
        <DialogContent className="max-w-md rounded-2xl p-6">
          <DialogHeader>
            <DialogTitle>Schedule Candidate Interview</DialogTitle>
            <DialogDescription>
              Set interview time with candidate {activeApp?.student?.full_name}.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleScheduleInterview} className="space-y-4 pt-2">
            <div className="space-y-2">
              <Label htmlFor="ivMode">Interview Mode</Label>
              <Select value={interviewMode} onValueChange={(v) => setInterviewMode(v as InterviewMode)}>
                <SelectTrigger id="ivMode" className="rounded-xl">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-xl">
                  <SelectItem value="ONLINE">Video Meeting (Online)</SelectItem>
                  <SelectItem value="PHONE">Phone Call</SelectItem>
                  <SelectItem value="IN_PERSON">In-Person</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="ivTime">Date & Time (Must be at least 24h in advance)</Label>
              <Input
                id="ivTime"
                type="datetime-local"
                value={scheduledAt}
                onChange={(e) => setScheduledAt(e.target.value)}
                required
                className="rounded-xl"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="ivDur">Duration (Minutes)</Label>
                <Input
                  id="ivDur"
                  type="number"
                  min="15"
                  max="180"
                  value={durationMin}
                  onChange={(e) => setDurationMin(Number(e.target.value))}
                  className="rounded-xl"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ivPanel">Interviewer</Label>
                <Input
                  id="ivPanel"
                  value={interviewerName}
                  onChange={(e) => setInterviewerName(e.target.value)}
                  placeholder="Panel Member"
                  className="rounded-xl"
                />
              </div>
            </div>

            {interviewMode === "ONLINE" && (
              <div className="space-y-2">
                <Label htmlFor="ivLink">Video Meeting Link (Google Meet / Zoom)</Label>
                <Input
                  id="ivLink"
                  type="url"
                  value={meetingLink}
                  onChange={(e) => setMeetingLink(e.target.value)}
                  placeholder="https://meet.google.com/..."
                  className="rounded-xl"
                />
              </div>
            )}

            <DialogFooter className="pt-4">
              <Button type="button" variant="outline" onClick={() => setScheduleOpen(false)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={createInterview.isPending} className="rounded-xl">
                Confirm Schedule
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Evaluation Dialog with Rubric Sliders */}
      <Dialog open={evalOpen} onOpenChange={setEvalOpen}>
        <DialogContent className="max-w-lg rounded-2xl p-6">
          <DialogHeader>
            <DialogTitle>Evaluate Candidate</DialogTitle>
            <DialogDescription>
              Assess {activeApp?.student?.full_name} using standard evaluation criteria.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmitEvaluation} className="space-y-5 pt-2">
            <div className="flex items-center justify-between rounded-xl bg-primary/10 p-3.5 text-sm">
              <span className="font-semibold text-foreground">Weighted Score</span>
              <span className="text-xl font-bold text-primary">{computeLiveScore()}%</span>
            </div>

            {defaultForm?.criteria?.map((c) => (
              <div key={c.id} className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-foreground">{c.name}</span>
                  <span className="text-muted-foreground">
                    Score: {scores[c.id] ?? 5} / {c.max_score || 10} (Weight: {c.weight})
                  </span>
                </div>
                <ScoreSlider
                  criterion={c}
                  value={scores[c.id] ?? 5}
                  onChange={(val) => handleScoreChange(c.id, val)}
                />
              </div>
            ))}

            <div className="space-y-2">
              <Label htmlFor="evalRec">Recommendation</Label>
              <Select value={evalRecommendation} onValueChange={(v) => setEvalRecommendation(v as EvaluationRecommendation)}>
                <SelectTrigger id="evalRec" className="rounded-xl">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-xl">
                  <SelectItem value="STRONG_YES">Strong Yes</SelectItem>
                  <SelectItem value="YES">Yes</SelectItem>
                  <SelectItem value="MAYBE">Maybe / Waitlist</SelectItem>
                  <SelectItem value="NO">No</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="evalNotes">Feedback & Notes</Label>
              <Textarea
                id="evalNotes"
                value={evalComments}
                onChange={(e) => setEvalComments(e.target.value)}
                placeholder="Key strengths, coding assessment results, and interview feedback..."
                rows={3}
                className="rounded-xl"
              />
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setEvalOpen(false)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={createEvaluation.isPending} className="rounded-xl">
                Submit Evaluation
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <DialogContent className="max-w-md rounded-2xl p-6">
          <DialogHeader>
            <DialogTitle>Reject Application</DialogTitle>
            <DialogDescription>
              Are you sure you want to reject {activeApp?.student?.full_name}?
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 pt-2">
            <Label htmlFor="rejReason">Optional Feedback / Reason</Label>
            <Textarea
              id="rejReason"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g. Position filled, missing required technical skills..."
              rows={3}
              className="rounded-xl"
            />
          </div>

          <DialogFooter className="pt-4">
            <Button variant="outline" onClick={() => setRejectOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                handleUpdateStatus("REJECTED", rejectReason);
                setRejectOpen(false);
              }}
              className="rounded-xl"
            >
              Confirm Rejection
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Offer / Accept Dialog */}
      <Dialog open={offerOpen} onOpenChange={setOfferOpen}>
        <DialogContent className="max-w-md rounded-2xl p-6">
          <DialogHeader>
            <DialogTitle>Extend Offer to Candidate</DialogTitle>
            <DialogDescription>
              Confirm offer terms for {activeApp?.student?.full_name}.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 pt-2">
            <div className="space-y-2">
              <Label htmlFor="offStipend">Confirmed Monthly Stipend (₹)</Label>
              <Input
                id="offStipend"
                type="number"
                value={offerStipend}
                onChange={(e) => setOfferStipend(e.target.value)}
                className="rounded-xl"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="offStart">Confirmed Start Date</Label>
              <Input
                id="offStart"
                type="date"
                value={offerStartDate}
                onChange={(e) => setOfferStartDate(e.target.value)}
                className="rounded-xl"
              />
            </div>
          </div>

          <DialogFooter className="pt-4">
            <Button variant="outline" onClick={() => setOfferOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button
              onClick={() => {
                handleUpdateStatus("ACCEPTED", `Offer extended: ₹${offerStipend}/mo starting ${offerStartDate}`);
                setOfferOpen(false);
              }}
              className="rounded-xl bg-emerald-600 hover:bg-emerald-700"
            >
              Extend Offer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
