"use client";

import { useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/shared/PageHeader";
import { CalendarView, type CalendarEvent } from "@/components/shared/CalendarView";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
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
  Building2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  MoreVertical,
} from "lucide-react";

export default function FacultyInterviewsPage() {
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
          reason: "Rescheduled by faculty interviewer",
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
      { id: cancelTarget.id, reason: cancelReason || "Cancelled by faculty" },
      {
        onSuccess: () => {
          toast.success("Interview cancelled.");
          setCancelTarget(null);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to cancel")),
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
          feedback_notes: feedbackNotes || undefined,
        },
      },
      {
        onSuccess: () => {
          toast.success("Interview result recorded.");
          setResultTarget(null);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to record result")),
      }
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Interview Management"
          description="Track upcoming interview rounds, launch video links, and record candidate results."
        />
        <div className="flex items-center gap-2">
          <Button
            variant={view === "list" ? "default" : "outline"}
            size="sm"
            onClick={() => setView("list")}
            className="rounded-xl gap-1.5"
          >
            <List className="size-4" /> List
          </Button>
          <Button
            variant={view === "calendar" ? "default" : "outline"}
            size="sm"
            onClick={() => setView("calendar")}
            className="rounded-xl gap-1.5"
          >
            <CalendarDays className="size-4" /> Calendar
          </Button>
        </div>
      </div>

      {isLoading ? (
        <LoadingCardGrid count={3} />
      ) : interviews.length === 0 ? (
        <EmptyState
          icon={Calendar}
          title="No interviews scheduled"
          description="When you schedule candidate interviews from the Candidate Review page, they will appear here."
        />
      ) : view === "calendar" ? (
        <Card className="rounded-2xl border-border/60 p-4 shadow-sm">
          <CalendarView events={calendarEvents} />
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {interviews.map((iv) => (
            <Card
              key={iv.id}
              className="flex flex-col justify-between rounded-2xl border-border/60 bg-card p-5 shadow-sm transition-all hover:border-primary/40"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge variant="outline" className="text-xs">
                    Round {iv.round || 1} • {iv.mode}
                  </Badge>
                  <Badge
                    variant="secondary"
                    className={`text-[10px] ${
                      iv.status === "SCHEDULED" ? "text-indigo-600 bg-indigo-50 dark:bg-indigo-950/40" : ""
                    }`}
                  >
                    {iv.status}
                  </Badge>
                </div>

                <div>
                  <h3 className="font-semibold text-base text-foreground">
                    {iv.application?.student?.full_name || "Candidate"}
                  </h3>
                  <p className="text-xs text-muted-foreground pt-0.5">
                    {iv.application?.internship?.title}
                  </p>
                </div>

                <div className="rounded-xl border bg-muted/20 p-3 space-y-1.5 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1.5 text-foreground font-medium">
                    <Clock className="size-4 text-primary" />
                    <span>{formatDate(iv.scheduled_at)}</span>
                  </div>
                  <div>Duration: {iv.duration_minutes} minutes</div>
                  {iv.result && (
                    <div className="font-semibold text-emerald-600 dark:text-emerald-400">
                      Result: {iv.result}
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-4 space-y-2">
                {iv.meeting_link && iv.status === "SCHEDULED" && (
                  <Button asChild size="sm" className="w-full gap-2 rounded-xl">
                    <a href={iv.meeting_link} target="_blank" rel="noopener noreferrer">
                      <Video className="size-4" /> Start Video Meeting
                    </a>
                  </Button>
                )}

                {iv.status === "SCHEDULED" && (
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setResultTarget(iv)}
                      className="flex-1 rounded-xl text-xs text-emerald-600 hover:text-emerald-700"
                    >
                      Record Result
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setRescheduleTarget(iv)}
                      className="rounded-xl text-xs"
                    >
                      Reschedule
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setCancelTarget(iv)}
                      className="rounded-xl text-xs text-muted-foreground hover:text-destructive"
                    >
                      Cancel
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Reschedule Modal */}
      <Dialog open={!!rescheduleTarget} onOpenChange={(o) => !o && setRescheduleTarget(null)}>
        <DialogContent className="max-w-md rounded-2xl p-6">
          <DialogHeader>
            <DialogTitle>Reschedule Interview</DialogTitle>
            <DialogDescription>
              Select a new date and time for {rescheduleTarget?.application?.student?.full_name}.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleReschedule} className="space-y-4 pt-2">
            <div className="space-y-2">
              <Label htmlFor="reschedTime">New Date & Time</Label>
              <Input
                id="reschedTime"
                type="datetime-local"
                value={newTime}
                onChange={(e) => setNewTime(e.target.value)}
                required
                className="rounded-xl"
              />
            </div>
            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setRescheduleTarget(null)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={reschedule.isPending} className="rounded-xl">
                Confirm Reschedule
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Record Result Modal */}
      <Dialog open={!!resultTarget} onOpenChange={(o) => !o && setResultTarget(null)}>
        <DialogContent className="max-w-md rounded-2xl p-6">
          <DialogHeader>
            <DialogTitle>Record Interview Outcome</DialogTitle>
            <DialogDescription>
              Submit the panel decision for {resultTarget?.application?.student?.full_name}.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleRecordResult} className="space-y-4 pt-2">
            <div className="space-y-2">
              <Label htmlFor="resSelect">Interview Result</Label>
              <Select value={selectedResult} onValueChange={(v) => setSelectedResult(v as InterviewResult)}>
                <SelectTrigger id="resSelect" className="rounded-xl">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-xl">
                  <SelectItem value="PASS">Pass / Cleared Round</SelectItem>
                  <SelectItem value="FAIL">Fail / Did Not Clear</SelectItem>
                  <SelectItem value="NO_SHOW">No Show</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="fbNotes">Evaluation Feedback / Notes</Label>
              <Textarea
                id="fbNotes"
                value={feedbackNotes}
                onChange={(e) => setFeedbackNotes(e.target.value)}
                placeholder="Technical competencies observed, communication, strengths..."
                rows={3}
                className="rounded-xl"
              />
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setResultTarget(null)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={recordResult.isPending} className="rounded-xl">
                Save Result
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Cancel Modal */}
      <Dialog open={!!cancelTarget} onOpenChange={(o) => !o && setCancelTarget(null)}>
        <DialogContent className="max-w-md rounded-2xl p-6">
          <DialogHeader>
            <DialogTitle>Cancel Interview</DialogTitle>
            <DialogDescription>
              Are you sure you want to cancel the interview for {cancelTarget?.application?.student?.full_name}?
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCancel} className="space-y-4 pt-2">
            <div className="space-y-2">
              <Label htmlFor="cancelReason">Reason for Cancellation</Label>
              <Textarea
                id="cancelReason"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="e.g. Panelist unavailable, candidate withdrew..."
                rows={3}
                className="rounded-xl"
              />
            </div>
            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setCancelTarget(null)} className="rounded-xl">
                Keep Interview
              </Button>
              <Button type="submit" variant="destructive" disabled={cancelIv.isPending} className="rounded-xl">
                Confirm Cancellation
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
