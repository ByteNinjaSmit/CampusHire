"use client";

import { useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { CalendarView, type CalendarEvent } from "@/components/shared/CalendarView";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useInterviews } from "@/lib/api/hooks/interviews";
import { formatDate, formatRelativeDate } from "@/lib/format";
import type { Interview } from "@/lib/api/types";
import {
  Calendar,
  Clock,
  Video,
  MapPin,
  Phone,
  User,
  Building2,
  CalendarDays,
  List,
  CheckCircle2,
  XCircle,
  ExternalLink,
} from "lucide-react";

export default function StudentInterviewsPage() {
  const [view, setView] = useState<"calendar" | "list">("list");
  const [selectedInterview, setSelectedInterview] = useState<Interview | null>(null);

  const { data, isLoading } = useInterviews({ page: 1, page_size: 50 });
  const interviews = data?.items ?? [];

  const calendarEvents: CalendarEvent[] = interviews.map((iv) => {
    const start = new Date(iv.scheduled_at);
    const end = new Date(start.getTime() + (iv.duration_minutes || 45) * 60 * 1000);
    return {
      id: iv.id,
      title: `${iv.internship?.title || "Interview"} (${iv.internship?.company_name || ""})`,
      start,
      end,
      status: iv.status,
      color: iv.status === "SCHEDULED" ? "indigo" : iv.status === "COMPLETED" ? "emerald" : "rose",
    };
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "SCHEDULED":
        return <Badge className="bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20">Scheduled</Badge>;
      case "COMPLETED":
        return <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20">Completed</Badge>;
      case "CANCELLED":
        return <Badge className="bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20">Cancelled</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getModeIcon = (mode: string) => {
    switch (mode) {
      case "ONLINE":
        return <Video className="size-4 text-indigo-500" />;
      case "PHONE":
        return <Phone className="size-4 text-amber-500" />;
      default:
        return <MapPin className="size-4 text-emerald-500" />;
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Interview Center"
          description="View your scheduled interview sessions, calendar invites, and video conferencing links."
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
          description="When recruiters shortlist your application and schedule an interview slot, it will appear here."
        />
      ) : view === "calendar" ? (
        <Card className="rounded-2xl border-border/60 p-4 shadow-sm">
          <CalendarView
            events={calendarEvents}
            onSelectEvent={(ev) => {
              const matched = interviews.find((i) => i.id === ev.id);
              if (matched) setSelectedInterview(matched);
            }}
          />
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {interviews.map((iv) => (
            <Card
              key={iv.id}
              className="flex flex-col justify-between rounded-2xl border-border/60 bg-card p-5 shadow-sm transition-all hover:border-primary/40 hover:shadow-md"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-muted-foreground uppercase">
                    Technical Round
                  </span>
                  {getStatusBadge(iv.status)}
                </div>

                <div>
                  <h3 className="font-semibold text-base text-foreground line-clamp-1">
                    {iv.internship?.title || "Technical Interview"}
                  </h3>
                  <p className="text-xs text-muted-foreground flex items-center gap-1.5 pt-0.5">
                    <Building2 className="size-3.5" />
                    {iv.internship?.company_name || "Company"}
                  </p>
                </div>

                <div className="rounded-xl border bg-muted/20 p-3 space-y-1.5 text-xs text-muted-foreground">
                  <div className="flex items-center gap-2 text-foreground font-medium">
                    <Clock className="size-4 text-primary" />
                    <span>{formatDate(iv.scheduled_at)}</span>
                  </div>
                  <div className="flex items-center justify-between pt-1">
                    <span className="flex items-center gap-1.5">
                      {getModeIcon(iv.mode)} {iv.mode}
                    </span>
                    <span>{iv.duration_minutes} minutes</span>
                  </div>
                  {iv.interviewer_name && (
                    <div className="flex items-center gap-1.5 pt-1 text-muted-foreground">
                      <User className="size-3.5" /> Interviewer: {iv.interviewer_name}
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-4 flex flex-col gap-2">
                {iv.meeting_link && iv.status === "SCHEDULED" && (
                  <Button asChild size="sm" className="w-full gap-2 rounded-xl">
                    <a href={iv.meeting_link} target="_blank" rel="noopener noreferrer">
                      <Video className="size-4" /> Join Video Meeting
                    </a>
                  </Button>
                )}

                {iv.application_id && (
                  <Button variant="outline" size="sm" asChild className="w-full rounded-xl text-xs">
                    <Link href={`/student/applications/${iv.application_id}`}>View Application Details</Link>
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Selected Interview Details Modal */}
      <Dialog open={!!selectedInterview} onOpenChange={(o) => !o && setSelectedInterview(null)}>
        <DialogContent className="max-w-lg rounded-2xl p-6">
          <DialogHeader>
            <DialogTitle>Interview Details</DialogTitle>
            <DialogDescription>
              {selectedInterview?.internship?.title} • {selectedInterview?.internship?.company_name}
            </DialogDescription>
          </DialogHeader>

          {selectedInterview && (
            <div className="space-y-4 pt-2 text-sm">
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="rounded-xl border p-3 bg-muted/20">
                  <span className="text-muted-foreground">Scheduled Time</span>
                  <p className="font-semibold text-foreground text-sm pt-0.5">
                    {formatDate(selectedInterview.scheduled_at)}
                  </p>
                </div>
                <div className="rounded-xl border p-3 bg-muted/20">
                  <span className="text-muted-foreground">Duration</span>
                  <p className="font-semibold text-foreground text-sm pt-0.5">
                    {selectedInterview.duration_minutes} minutes
                  </p>
                </div>
              </div>

              <div className="rounded-xl border p-3.5 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Interview Mode</span>
                  <span className="font-semibold text-foreground">{selectedInterview.mode}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Status</span>
                  <span className="font-semibold text-foreground">{selectedInterview.status}</span>
                </div>
                {selectedInterview.interviewer_name && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Interviewer</span>
                    <span className="font-semibold text-foreground">{selectedInterview.interviewer_name}</span>
                  </div>
                )}
              </div>

              {selectedInterview.meeting_link && (
                <Button asChild className="w-full gap-2 rounded-xl">
                  <a href={selectedInterview.meeting_link} target="_blank" rel="noopener noreferrer">
                    <Video className="size-4" /> Open Meeting Link
                  </a>
                </Button>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
