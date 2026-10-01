"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useInternship, useInternshipApplications } from "@/lib/api/hooks/internships";
import {
  useUpdateApplicationStatus,
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
import type { ApplicationStatus, InterviewMode, EvaluationRecommendation } from "@/lib/api/types";
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

export default function CompanyCandidateReviewPage() {
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
    if (!activeApp) return;
    if (!scheduledAt) {
      toast.error("Please pick an interview date and time");
      return;
    }

    createInterview.mutate(
      {
        application_id: activeApp.id,
        scheduled_at: scheduledAt.includes("Z") ? scheduledAt : `${scheduledAt}:00Z`,
        duration_minutes: Number(durationMin),
        mode: interviewMode,
        meeting_link: interviewMode === "ONLINE" ? meetingLink : undefined,
        location: interviewMode === "ONSITE" ? meetingLink || "Company HQ" : undefined,
        interviewer_name: interviewerName.trim() || undefined,
      },
      {
        onSuccess: () => {
          toast.success("Interview scheduled and invite sent to candidate");
          setScheduleOpen(false);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to schedule interview")),
      }
    );
  };

  const handleSaveEvaluation = (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeApp || !defaultForm) return;

    const criteriaList = defaultForm.criteria.map((c) => ({
      criterion_id: c.id,
      score: scores[c.id] ?? 8,
    }));

    createEvaluation.mutate(
      {
        application_id: activeApp.id,
        form_id: defaultForm.id,
        scores: criteriaList,
        recommendation: evalRecommendation,
        comments: evalComments.trim(),
        shared_with_student: true,
      },
      {
        onSuccess: () => {
          toast.success("Evaluation rubric saved successfully");
          setEvalOpen(false);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to save evaluation")),
      }
    );
  };

  const handleSendOffer = (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeApp) return;

    updateStatus.mutate(
      {
        id: activeApp.id,
        body: {
          status: "ACCEPTED",
          note: `Official offer extended with monthly stipend of ₹${offerStipend || internship?.stipend_monthly}. Start Date: ${offerStartDate}`,
        },
      },
      {
        onSuccess: () => {
          toast.success("Candidate accepted and offer letter recorded!");
          setOfferOpen(false);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to extend offer")),
      }
    );
  };

  const handleRejectCandidate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeApp) return;

    updateStatus.mutate(
      {
        id: activeApp.id,
        body: {
          status: "REJECTED",
          note: rejectReason.trim() || "Candidate profile does not match current requirements.",
        },
      },
      {
        onSuccess: () => {
          toast.info("Candidate rejected");
          setRejectOpen(false);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to reject candidate")),
      }
    );
  };

  if (isInternshipLoading || isAppsLoading) {
    return <LoadingCardGrid count={3} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link
            href="/company/internships"
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-2 transition-colors"
          >
            <ArrowLeft className="size-3.5" /> Back to company postings
          </Link>
          <PageHeader
            title={internship ? `Candidate Review: ${internship.title}` : "Candidate Review"}
            description={`${applications.length} applicants total • ${internship?.openings || 1} openings`}
          />
        </div>

        {activeApp && (
          <div className="flex flex-wrap items-center gap-2">
            {activeApp.status === "PENDING" && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleUpdateStatus("UNDER_REVIEW")}
                className="rounded-xl text-xs gap-1.5"
              >
                <Clock className="size-3.5 text-sky-500" /> Move to Review
              </Button>
            )}

            {["PENDING", "UNDER_REVIEW"].includes(activeApp.status) && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleUpdateStatus("SHORTLISTED")}
                className="rounded-xl text-xs gap-1.5 text-violet-600 dark:text-violet-400"
              >
                <CheckCircle2 className="size-3.5" /> Shortlist
              </Button>
            )}

            {["UNDER_REVIEW", "SHORTLISTED", "INTERVIEW"].includes(activeApp.status) && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setScheduleOpen(true)}
                className="rounded-xl text-xs gap-1.5 text-amber-600 dark:text-amber-400"
              >
                <Calendar className="size-3.5" /> Schedule Interview
              </Button>
            )}

            <Button
              size="sm"
              variant="outline"
              onClick={() => setEvalOpen(true)}
              className="rounded-xl text-xs gap-1.5"
            >
              <Award className="size-3.5 text-primary" /> Evaluate
            </Button>

            {activeApp.status !== "ACCEPTED" && (
              <Button
                size="sm"
                variant="default"
                onClick={() => setOfferOpen(true)}
                className="rounded-xl text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                <CheckCircle2 className="size-3.5" /> Extend Offer
              </Button>
            )}

            {activeApp.status !== "REJECTED" && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setRejectOpen(true)}
                className="rounded-xl text-xs text-muted-foreground hover:text-destructive"
              >
                <XCircle className="size-3.5" /> Reject
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Split Screen Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[750px]">
        {/* Left Column: Applicant Filter & List */}
        <div className="lg:col-span-4 flex flex-col space-y-3">
          <Card className="rounded-2xl border-border/60 shadow-sm p-3 space-y-3">
            <SearchInput
              value={search}
              onChange={setSearch}
              placeholder="Search candidate name, dept..."
            />

            <div className="flex items-center gap-2">
              <Filter className="size-3.5 text-muted-foreground" />
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="h-8 rounded-lg text-xs">
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent className="rounded-xl">
                  <SelectItem value="ALL">All Applicants ({appsData?.items?.length ?? 0})</SelectItem>
                  <SelectItem value="PENDING">Pending</SelectItem>
                  <SelectItem value="UNDER_REVIEW">Under Review</SelectItem>
                  <SelectItem value="SHORTLISTED">Shortlisted</SelectItem>
                  <SelectItem value="INTERVIEW">Interview</SelectItem>
                  <SelectItem value="ACCEPTED">Accepted / Placed</SelectItem>
                  <SelectItem value="REJECTED">Rejected</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </Card>

          {/* Candidates Scroll List */}
          <div className="flex-1 space-y-2 overflow-y-auto max-h-[700px] pr-1">
            {applications.length === 0 ? (
              <EmptyState
                icon={Users}
                title="No candidates"
                description="No applications match the current filter."
              />
            ) : (
              applications.map((app) => {
                const isSelected = app.id === (activeApp?.id ?? "");
                return (
                  <button
                    key={app.id}
                    type="button"
                    onClick={() => setSelectedAppId(app.id)}
                    className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                      isSelected
                        ? "border-primary bg-primary/5 shadow-xs ring-1 ring-primary/20"
                        : "border-border/60 bg-card hover:bg-muted/40"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="font-semibold text-sm text-foreground">
                          {app.student?.full_name || "Applicant"}
                        </h4>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {app.student?.department} • GPA:{" "}
                          <span className="font-medium text-foreground">{app.student?.gpa ?? "N/A"}</span>
                        </p>
                      </div>
                      <StatusBadge status={app.status} />
                    </div>

                    <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-border/30 text-[11px] text-muted-foreground">
                      <span>Applied {formatRelativeDate(app.created_at)}</span>
                      {app.interviews && app.interviews.length > 0 && (
                        <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400 font-medium">
                          <Calendar className="size-3" /> Interviewed
                        </span>
                      )}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Detailed Candidate View */}
        <div className="lg:col-span-8">
          {!activeApp ? (
            <Card className="h-full flex items-center justify-center p-8 rounded-2xl border-border/60">
              <EmptyState
                icon={Users}
                title="Select a Candidate"
                description="Choose an applicant from the left column to view resume, qualifications, and recruitment history."
              />
            </Card>
          ) : (
            <Card className="rounded-2xl border-border/60 shadow-sm overflow-hidden flex flex-col h-full">
              {/* Header Info */}
              <div className="p-6 border-b border-border/60 bg-muted/10 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold text-lg">
                      {activeApp.student?.full_name?.[0]?.toUpperCase() || "S"}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-lg font-bold text-foreground">
                          {activeApp.student?.full_name}
                        </h2>
                        <StatusBadge status={activeApp.status} />
                      </div>
                      <p className="text-xs text-muted-foreground flex items-center gap-2 mt-0.5">
                        <span>{activeApp.student?.department}</span>
                        <span>•</span>
                        <span>Enrollment: {activeApp.student?.enrollment_no || "N/A"}</span>
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                    <div className="flex items-center gap-1.5">
                      <GraduationCap className="size-4 text-primary" />
                      <span>
                        GPA: <strong className="text-foreground">{activeApp.student?.gpa ?? "N/A"}</strong>
                      </span>
                    </div>
                    {activeApp.student?.email && (
                      <a
                        href={`mailto:${activeApp.student.email}`}
                        className="flex items-center gap-1 hover:text-foreground transition-colors"
                      >
                        <Mail className="size-3.5" /> Email
                      </a>
                    )}
                    {activeApp.student?.phone && (
                      <span className="flex items-center gap-1">
                        <Phone className="size-3.5" /> {activeApp.student.phone}
                      </span>
                    )}
                  </div>
                </div>

                {/* Candidate Skills */}
                {activeApp.student?.skills && activeApp.student.skills.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    <span className="text-xs text-muted-foreground mr-1">Skills:</span>
                    {activeApp.student.skills.map((s) => (
                      <Badge key={s} variant="secondary" className="text-[11px] rounded-md">
                        {s}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              {/* Tabs Section */}
              <Tabs defaultValue="resume" className="flex-1 flex flex-col p-6">
                <TabsList className="rounded-xl w-fit mb-4">
                  <TabsTrigger value="resume" className="rounded-lg gap-1.5">
                    <FileText className="size-3.5" /> Resume PDF
                  </TabsTrigger>
                  <TabsTrigger value="coverLetter" className="rounded-lg gap-1.5">
                    Cover Letter
                  </TabsTrigger>
                  <TabsTrigger value="history" className="rounded-lg gap-1.5">
                    Timeline History
                  </TabsTrigger>
                  <TabsTrigger value="interviews" className="rounded-lg gap-1.5">
                    Interviews ({activeApp.interviews?.length || 0})
                  </TabsTrigger>
                </TabsList>

                {/* Resume PDF Tab */}
                <TabsContent value="resume" className="flex-1 mt-0">
                  {activeApp.resume_document_id ? (
                    <div className="h-[600px] rounded-xl border border-border/60 overflow-hidden">
                      <PdfViewer documentId={activeApp.resume_document_id} title="Candidate Resume" />
                    </div>
                  ) : (
                    <EmptyState
                      icon={FileText}
                      title="No Resume Attached"
                      description="This applicant did not attach an uploaded PDF resume."
                    />
                  )}
                </TabsContent>

                {/* Cover Letter Tab */}
                <TabsContent value="coverLetter" className="space-y-4 mt-0">
                  <Card className="rounded-xl p-5 border-border/60 bg-muted/20">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                      Statement of Interest / Cover Letter
                    </h4>
                    {activeApp.cover_letter ? (
                      <p className="text-sm leading-relaxed whitespace-pre-line text-foreground">
                        {activeApp.cover_letter}
                      </p>
                    ) : (
                      <p className="text-sm italic text-muted-foreground">
                        No cover letter provided by candidate.
                      </p>
                    )}
                  </Card>
                </TabsContent>

                {/* Timeline History Tab */}
                <TabsContent value="history" className="space-y-4 mt-0">
                  <Card className="rounded-xl p-5 border-border/60">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">
                      Application Workflow Stepper
                    </h4>
                    <ApplicationTimeline
                      currentStatus={activeApp.status}
                      history={activeApp.history || []}
                    />
                  </Card>
                </TabsContent>

                {/* Interviews Tab */}
                <TabsContent value="interviews" className="space-y-4 mt-0">
                  {!activeApp.interviews || activeApp.interviews.length === 0 ? (
                    <EmptyState
                      icon={Calendar}
                      title="No Interviews Scheduled"
                      description="No interview sessions have been booked for this candidate yet."
                      action={
                        <Button onClick={() => setScheduleOpen(true)} className="rounded-xl text-xs gap-1.5">
                          <Calendar className="size-3.5" /> Book Interview Slot
                        </Button>
                      }
                    />
                  ) : (
                    <div className="space-y-3">
                      {activeApp.interviews.map((iv) => (
                        <div
                          key={iv.id}
                          className="p-4 rounded-xl border border-border/60 bg-card flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                        >
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="text-xs font-semibold">
                                {iv.mode}
                              </Badge>
                              <span className="font-semibold text-sm">
                                {formatDate(iv.scheduled_at)}
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground">
                              Duration: {iv.duration_minutes} min • Interviewer: {iv.interviewer_name || "Hiring Team"}
                            </p>
                          </div>

                          <div className="flex items-center gap-2">
                            {iv.meeting_link && (
                              <Button size="sm" variant="outline" asChild className="rounded-xl text-xs gap-1">
                                <a href={iv.meeting_link} target="_blank" rel="noopener noreferrer">
                                  <Video className="size-3.5" /> Meeting Link <ExternalLink className="size-3" />
                                </a>
                              </Button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </Card>
          )}
        </div>
      </div>

      {/* Schedule Interview Dialog */}
      <Dialog open={scheduleOpen} onOpenChange={setScheduleOpen}>
        <DialogContent className="rounded-2xl sm:max-w-md">
          <form onSubmit={handleScheduleInterview}>
            <DialogHeader>
              <DialogTitle>Schedule Candidate Interview</DialogTitle>
              <DialogDescription>
                Set date, time, and meeting details for {activeApp?.student?.full_name}.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="ivMode">Interview Mode</Label>
                <Select value={interviewMode} onValueChange={(v) => setInterviewMode(v as InterviewMode)}>
                  <SelectTrigger id="ivMode" className="rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl">
                    <SelectItem value="ONLINE">Online Video Call</SelectItem>
                    <SelectItem value="ONSITE">On-Site Campus / Office</SelectItem>
                    <SelectItem value="PHONE">Phone Interview</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="ivTime">Date & Time</Label>
                  <Input
                    id="ivTime"
                    type="datetime-local"
                    value={scheduledAt}
                    onChange={(e) => setScheduledAt(e.target.value)}
                    required
                    className="rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ivDuration">Duration (min)</Label>
                  <Input
                    id="ivDuration"
                    type="number"
                    min="15"
                    step="15"
                    value={durationMin}
                    onChange={(e) => setDurationMin(Number(e.target.value))}
                    required
                    className="rounded-xl"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="ivInterviewer">Interviewer Name</Label>
                <Input
                  id="ivInterviewer"
                  value={interviewerName}
                  onChange={(e) => setInterviewerName(e.target.value)}
                  placeholder="e.g. Lead Engineer / Recruiter"
                  className="rounded-xl"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="ivLink">
                  {interviewMode === "ONLINE" ? "Meeting URL (Google Meet / Zoom)" : "Physical Location"}
                </Label>
                <Input
                  id="ivLink"
                  value={meetingLink}
                  onChange={(e) => setMeetingLink(e.target.value)}
                  placeholder={interviewMode === "ONLINE" ? "https://meet.google.com/..." : "Office Room 302"}
                  required={interviewMode === "ONLINE"}
                  className="rounded-xl"
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setScheduleOpen(false)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={createInterview.isPending} className="rounded-xl">
                {createInterview.isPending ? "Scheduling..." : "Send Invitation"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Rubric Evaluation Dialog */}
      <Dialog open={evalOpen} onOpenChange={setEvalOpen}>
        <DialogContent className="rounded-2xl sm:max-w-xl max-h-[85vh] overflow-y-auto">
          <form onSubmit={handleSaveEvaluation}>
            <DialogHeader>
              <DialogTitle>Candidate Evaluation Rubric</DialogTitle>
              <DialogDescription>
                Score {activeApp?.student?.full_name} on standard hiring criteria.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-5 py-4">
              {defaultForm?.criteria?.map((c) => (
                <div key={c.id} className="space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-semibold text-foreground">{c.name}</span>
                    <span className="text-muted-foreground">Weight: {c.weight}%</span>
                  </div>
                  <ScoreSlider
                    value={scores[c.id] ?? 8}
                    max={c.max_score || 10}
                    onChange={(val) => setScores({ ...scores, [c.id]: val })}
                  />
                  {c.description && (
                    <p className="text-[11px] text-muted-foreground">{c.description}</p>
                  )}
                </div>
              ))}

              <div className="space-y-2 pt-2 border-t border-border/40">
                <Label>Hiring Recommendation</Label>
                <Select value={evalRecommendation} onValueChange={(v) => setEvalRecommendation(v as EvaluationRecommendation)}>
                  <SelectTrigger className="rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl">
                    <SelectItem value="STRONG_YES">Strong Yes (Immediate Offer)</SelectItem>
                    <SelectItem value="YES">Yes (Recommended)</SelectItem>
                    <SelectItem value="MAYBE">Maybe (Backup Candidate)</SelectItem>
                    <SelectItem value="NO">No (Do Not Recommend)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="evalComments">Evaluation Notes & Strengths</Label>
                <Textarea
                  id="evalComments"
                  rows={3}
                  value={evalComments}
                  onChange={(e) => setEvalComments(e.target.value)}
                  placeholder="Technical depth, communication, problem solving observations..."
                  className="rounded-xl"
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setEvalOpen(false)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={createEvaluation.isPending} className="rounded-xl">
                {createEvaluation.isPending ? "Submitting..." : "Submit Evaluation"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Extend Offer Dialog */}
      <Dialog open={offerOpen} onOpenChange={setOfferOpen}>
        <DialogContent className="rounded-2xl sm:max-w-md">
          <form onSubmit={handleSendOffer}>
            <DialogHeader>
              <DialogTitle>Extend Formal Offer</DialogTitle>
              <DialogDescription>
                Extend an internship offer to {activeApp?.student?.full_name}. This moves the application to ACCEPTED status.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="offerStipend">Confirmed Monthly Stipend (₹)</Label>
                <Input
                  id="offerStipend"
                  type="number"
                  value={offerStipend}
                  onChange={(e) => setOfferStipend(e.target.value)}
                  required
                  className="rounded-xl"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="offerStart">Internship Start Date</Label>
                <Input
                  id="offerStart"
                  type="date"
                  value={offerStartDate}
                  onChange={(e) => setOfferStartDate(e.target.value)}
                  required
                  className="rounded-xl"
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOfferOpen(false)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={updateStatus.isPending} className="rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white">
                {updateStatus.isPending ? "Confirming..." : "Confirm & Extend Offer"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Reject Candidate Dialog */}
      <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <DialogContent className="rounded-2xl sm:max-w-md">
          <form onSubmit={handleRejectCandidate}>
            <DialogHeader>
              <DialogTitle>Reject Application</DialogTitle>
              <DialogDescription>
                Provide feedback or reason for rejecting {activeApp?.student?.full_name}.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="rejectReason">Rejection Feedback / Notes</Label>
                <Textarea
                  id="rejectReason"
                  rows={3}
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="e.g. Role filled or candidate lacks specific technology experience..."
                  required
                  className="rounded-xl"
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setRejectOpen(false)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" variant="destructive" disabled={updateStatus.isPending} className="rounded-xl">
                {updateStatus.isPending ? "Updating..." : "Confirm Rejection"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
