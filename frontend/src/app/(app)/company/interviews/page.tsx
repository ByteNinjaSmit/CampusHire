"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { CalendarView, type CalendarEvent } from "@/components/shared/CalendarView";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  useInterviews,
  useRescheduleInterview,
  useCancelInterview,
  useRecordInterviewResult,
} from "@/lib/api/hooks/interviews";
import { formatDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import type { Interview, InterviewResult } from "@/lib/api/types";
import {
  Calendar,
  Clock,
  Video,
  List,
  CalendarDays,
  User,
  CheckCircle2,
  XCircle,
  ExternalLink,
} from "lucide-react";

export default function CompanyInterviewsPage() {
  const [view, setView] = useState<"calendar" | "list">("list");
  const { data, isLoading, refetch } = useInterviews({ page: 1, page_size: 100 });
  const interviews = data?.items ?? [];

  const reschedule = useRescheduleInterview();
  const cancelIv = useCancelInterview();
  const recordResult = useRecordInterviewResult();

  // Action Dialog States
  const [rescheduleTarget, setRescheduleTarget] = useState<Interview | null>(null);
  const [newTime, setNewTime] = useState("");
  const [cancelTarget, setCancelTarget] = useState<Interview | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [resultTarget, setResultTarget] = useState<Interview | null>(null);
  const [selectedResult, setSelectedResult] = useState<InterviewResult>("PASS");
  const [feedbackNotes, setFeedbackNotes] = useState("");

  const calendarEvents: CalendarEvent[] = interviews.map((iv) => {
    const start = new Date(iv.scheduled_at);
    const end = new Date(start.getTime() + (iv.duration_minutes || 45) * 60 * 1000);
    return {
      id: iv.id,
      title: `${iv.application?.student?.full_name || "Candidate"} - ${iv.application?.internship?.title || "Role"}`,
      start,
      end,
      status: iv.status,
      color: iv.status === "SCHEDULED" ? "indigo" : iv.status === "COMPLETED" ? "emerald" : "rose",
    };
  });

  const handleReschedule = (e: React.FormEvent) => {
    e.preventDefault();
    if (!rescheduleTarget || !newTime) return;
    reschedule.mutate(
      {
        id: rescheduleTarget.id,
        body: {
          scheduled_at: newTime.includes("Z") ? newTime : `${newTime}:00Z`,
          reason: "Rescheduled by company interviewer",
        },
      },
      {
        onSuccess: () => {
          toast.success("Interview rescheduled and candidate notified.");
          setRescheduleTarget(null);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to reschedule")),
      }
    );
  };

  const handleCancel = (e: React.FormEvent) => {
    e.preventDefault();
    if (!cancelTarget) return;
    cancelIv.mutate(
      { id: cancelTarget.id, reason: cancelReason || "Cancelled by company" },
      {
        onSuccess: () => {
          toast.info("Interview cancelled");
          setCancelTarget(null);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to cancel interview")),
      }
    );
  };

  const handleRecordResult = (e: React.FormEvent) => {
    e.preventDefault();
    if (!resultTarget) return;
    recordResult.mutate(
      {
        id: resultTarget.id,
        body: {
          result: selectedResult,
          feedback_for_student: feedbackNotes.trim() || undefined,
        },
      },
      {
        onSuccess: () => {
          toast.success(`Result recorded as ${selectedResult}`);
          setResultTarget(null);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to record interview result")),
      }
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Company Interview Center"
          description="Manage technical interviews, book candidate slots, and record evaluation outcomes."
        />

        <div className="flex items-center gap-2 rounded-xl border border-border/60 bg-card p-1 shadow-xs">
          <Button
            size="sm"
            variant={view === "list" ? "secondary" : "ghost"}
            onClick={() => setView("list")}
            className="rounded-lg text-xs gap-1.5"
          >
            <List className="size-3.5" /> List View
          </Button>
          <Button
            size="sm"
            variant={view === "calendar" ? "secondary" : "ghost"}
            onClick={() => setView("calendar")}
            className="rounded-lg text-xs gap-1.5"
          >
            <CalendarDays className="size-3.5" /> Calendar View
          </Button>
        </div>
      </div>

      {isLoading ? (
        <LoadingCardGrid count={3} />
      ) : interviews.length === 0 ? (
        <EmptyState
          icon={Calendar}
          title="No interviews scheduled"
          description="You don't have any candidate interviews scheduled yet. Open a candidate review to schedule one."
        />
      ) : view === "calendar" ? (
        <Card className="p-6 rounded-2xl border-border/60 shadow-sm">
          <CalendarView events={calendarEvents} />
        </Card>
      ) : (
        <div className="divide-y divide-border/60 rounded-2xl border border-border/60 bg-card shadow-sm">
          {interviews.map((iv) => (
            <div
              key={iv.id}
              className="flex flex-col gap-4 p-5 transition-colors hover:bg-muted/30 lg:flex-row lg:items-center lg:justify-between"
            >
              <div className="flex items-start gap-4">
                <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold shadow-xs">
                  <User className="size-6" />
                </div>

                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-base text-foreground">
                      {iv.application?.student?.full_name || "Candidate"}
                    </span>
                    <Badge
                      variant="outline"
                      className={`text-xs font-semibold ${
                        iv.status === "SCHEDULED"
                          ? "border-amber-500/30 text-amber-600 bg-amber-500/10"
                          : iv.status === "COMPLETED"
                          ? "border-emerald-500/30 text-emerald-600 bg-emerald-500/10"
                          : "border-rose-500/30 text-rose-600 bg-rose-500/10"
                      }`}
                    >
                      {iv.status}
                    </Badge>
                    {iv.result && iv.result !== "PENDING" && (
                      <Badge
                        variant="outline"
                        className={`text-xs font-semibold ${
                          iv.result === "PASS"
                            ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/20"
                            : "bg-rose-500/10 text-rose-600 border-rose-500/20"
                        }`}
                      >
                        Result: {iv.result}
                      </Badge>
                    )}
                  </div>

                  <p className="text-xs text-muted-foreground">
                    Role: <strong className="text-foreground">{iv.application?.internship?.title || "Internship"}</strong> • Mode:{" "}
                    <span className="font-medium text-foreground">{iv.mode}</span>
                  </p>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground pt-1">
                    <span className="flex items-center gap-1">
                      <Clock className="size-3.5 text-primary" /> {formatDate(iv.scheduled_at)}
                    </span>
                    <span>•</span>
                    <span>{iv.duration_minutes} Minutes</span>
                    <span>•</span>
                    <span>Interviewer: {iv.interviewer_name || "Hiring Team"}</span>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 self-start lg:self-center">
                {iv.meeting_link && (
                  <Button size="sm" variant="outline" asChild className="rounded-xl text-xs gap-1.5">
                    <a href={iv.meeting_link} target="_blank" rel="noopener noreferrer">
                      <Video className="size-3.5 text-primary" /> Join Session <ExternalLink className="size-3" />
                    </a>
                  </Button>
                )}

                {iv.status === "SCHEDULED" && (
                  <>
                    <Button
                      size="sm"
                      variant="default"
                      onClick={() => {
                        setResultTarget(iv);
                        setSelectedResult("PASS");
                        setFeedbackNotes("");
                      }}
                      className="rounded-xl text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white"
                    >
                      <CheckCircle2 className="size-3.5" /> Record Outcome
                    </Button>

                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setRescheduleTarget(iv);
                        setNewTime(iv.scheduled_at.substring(0, 16));
                      }}
                      className="rounded-xl text-xs gap-1.5"
                    >
                      <Clock className="size-3.5" /> Reschedule
                    </Button>

                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setCancelTarget(iv);
                        setCancelReason("");
                      }}
                      className="rounded-xl text-xs text-muted-foreground hover:text-destructive"
                    >
                      <XCircle className="size-3.5" /> Cancel
                    </Button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Reschedule Dialog */}
      <Dialog open={!!rescheduleTarget} onOpenChange={(o) => !o && setRescheduleTarget(null)}>
        <DialogContent className="rounded-2xl sm:max-w-md">
          <form onSubmit={handleReschedule}>
            <DialogHeader>
              <DialogTitle>Reschedule Interview</DialogTitle>
              <DialogDescription>
                Select a new date and time for {rescheduleTarget?.application?.student?.full_name}.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="rescheduleTime">New Date & Time</Label>
                <Input
                  id="rescheduleTime"
                  type="datetime-local"
                  value={newTime}
                  onChange={(e) => setNewTime(e.target.value)}
                  required
                  className="rounded-xl"
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setRescheduleTarget(null)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={reschedule.isPending} className="rounded-xl">
                {reschedule.isPending ? "Rescheduling..." : "Confirm New Slot"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Cancel Dialog */}
      <Dialog open={!!cancelTarget} onOpenChange={(o) => !o && setCancelTarget(null)}>
        <DialogContent className="rounded-2xl sm:max-w-md">
          <form onSubmit={handleCancel}>
            <DialogHeader>
              <DialogTitle>Cancel Interview</DialogTitle>
              <DialogDescription>
                Are you sure you want to cancel the interview with {cancelTarget?.application?.student?.full_name}?
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="cancelReason">Reason for Cancellation</Label>
                <Textarea
                  id="cancelReason"
                  rows={3}
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  placeholder="e.g. Position filled or scheduling conflict"
                  required
                  className="rounded-xl"
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCancelTarget(null)} className="rounded-xl">
                Keep Interview
              </Button>
              <Button type="submit" variant="destructive" disabled={cancelIv.isPending} className="rounded-xl">
                {cancelIv.isPending ? "Cancelling..." : "Confirm Cancellation"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Record Result Dialog */}
      <Dialog open={!!resultTarget} onOpenChange={(o) => !o && setResultTarget(null)}>
        <DialogContent className="rounded-2xl sm:max-w-md">
          <form onSubmit={handleRecordResult}>
            <DialogHeader>
              <DialogTitle>Record Interview Outcome</DialogTitle>
              <DialogDescription>
                Log the technical interview outcome for {resultTarget?.application?.student?.full_name}.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="ivResult">Interview Verdict</Label>
                <Select value={selectedResult} onValueChange={(v) => setSelectedResult(v as InterviewResult)}>
                  <SelectTrigger id="ivResult" className="rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl">
                    <SelectItem value="PASS">Pass (Recommended for Offer)</SelectItem>
                    <SelectItem value="FAIL">Fail (Did not meet bar)</SelectItem>
                    <SelectItem value="ON_HOLD">On Hold (Pending additional rounds)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="feedback">Candidate Notes & Feedback</Label>
                <Textarea
                  id="feedback"
                  rows={4}
                  value={feedbackNotes}
                  onChange={(e) => setFeedbackNotes(e.target.value)}
                  placeholder="Provide constructive feedback on technical skills, coding proficiency, and communication..."
                  className="rounded-xl"
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setResultTarget(null)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={recordResult.isPending} className="rounded-xl">
                {recordResult.isPending ? "Recording..." : "Save Outcome"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
