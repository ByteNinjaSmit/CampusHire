"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { SearchInput } from "@/components/shared/SearchInput";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingTableSkeleton } from "@/components/shared/LoadingSkeletons";
import { StatCard } from "@/components/shared/StatCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  useSystemFeedback,
  useSystemFeedbackSummary,
  useUpdateSystemFeedback,
  useAddActionItem,
  useUpdateActionItem,
} from "@/lib/api/hooks/feedback";
import { formatDate, formatRelativeDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import type { SystemFeedback, ActionItem } from "@/lib/api/types";
import {
  Star,
  Bug,
  Lightbulb,
  Sparkles,
  CheckCircle2,
  Clock,
  ListTodo,
  Plus,
  ArrowRight,
  Filter,
} from "lucide-react";

export default function AdminFeedbackPage() {
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [typeFilter, setTypeFilter] = useState<string>("ALL");
  const [search, setSearch] = useState("");

  const { data: summary } = useSystemFeedbackSummary();
  const { data: feedbackData, isLoading, refetch } = useSystemFeedback({
    status: statusFilter !== "ALL" ? (statusFilter as SystemFeedback["status"]) : undefined,
    type: typeFilter !== "ALL" ? (typeFilter as SystemFeedback["type"]) : undefined,
    page: 1,
    page_size: 50,
  });

  const updateFeedback = useUpdateSystemFeedback();
  const addActionItem = useAddActionItem();
  const updateActionItem = useUpdateActionItem();

  // Triage Dialog
  const [triageTarget, setTriageTarget] = useState<SystemFeedback | null>(null);
  const [triageStatus, setTriageStatus] = useState<SystemFeedback["status"]>("TRIAGED");
  const [triagePriority, setTriagePriority] = useState<SystemFeedback["priority"]>("MEDIUM");
  const [adminNotes, setAdminNotes] = useState("");

  // New Action Item state inside dialog
  const [newActionTitle, setNewActionTitle] = useState("");

  const items = (feedbackData?.items ?? []).filter((fb) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      fb.title.toLowerCase().includes(q) ||
      fb.description.toLowerCase().includes(q) ||
      fb.user?.full_name?.toLowerCase().includes(q)
    );
  });

  const handleUpdateTriage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!triageTarget) return;

    updateFeedback.mutate(
      {
        id: triageTarget.id,
        body: {
          status: triageStatus,
          priority: triagePriority,
          admin_notes: adminNotes.trim() || undefined,
        },
      },
      {
        onSuccess: () => {
          toast.success("Feedback triage status updated");
          setTriageTarget(null);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to update feedback triage")),
      }
    );
  };

  const handleAddAction = (feedbackId: string) => {
    if (!newActionTitle.trim()) return;
    addActionItem.mutate(
      { id: feedbackId, body: { title: newActionTitle.trim() } },
      {
        onSuccess: () => {
          toast.success("Action item assigned");
          setNewActionTitle("");
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to add action item")),
      }
    );
  };

  const handleToggleActionStatus = (action: ActionItem) => {
    const nextStatus = action.status === "DONE" ? "OPEN" : "DONE";
    updateActionItem.mutate(
      { id: action.id, body: { status: nextStatus } },
      {
        onSuccess: () => {
          toast.success(`Action item marked ${nextStatus}`);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to update action item")),
      }
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="System Feedback Triage Board"
          description="Review bug reports, feature suggestions, and usability feedback submitted by campus users."
        />
      </div>

      {/* Summary KPI Strip */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Open Bugs"
          value={summary?.by_type?.BUG ?? 0}
          icon={Bug}
          format="number"
        />
        <StatCard
          label="Feature Ideas"
          value={summary?.by_type?.FEATURE ?? 0}
          icon={Lightbulb}
          format="number"
        />
        <StatCard
          label="Active Triaged"
          value={summary?.by_status?.TRIAGED ?? 0}
          icon={Sparkles}
          format="number"
        />
        <StatCard
          label="Open Action Items"
          value={summary?.open_action_items ?? 0}
          icon={ListTodo}
          format="number"
        />
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-36 rounded-xl">
              <SelectValue placeholder="All Types" />
            </SelectTrigger>
            <SelectContent className="rounded-xl">
              <SelectItem value="ALL">All Types</SelectItem>
              <SelectItem value="BUG">Bugs</SelectItem>
              <SelectItem value="FEATURE">Features</SelectItem>
              <SelectItem value="IMPROVEMENT">Improvements</SelectItem>
            </SelectContent>
          </Select>

          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-36 rounded-xl">
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent className="rounded-xl">
              <SelectItem value="ALL">All Statuses</SelectItem>
              <SelectItem value="NEW">New</SelectItem>
              <SelectItem value="TRIAGED">Triaged</SelectItem>
              <SelectItem value="PLANNED">Planned</SelectItem>
              <SelectItem value="IN_PROGRESS">In Progress</SelectItem>
              <SelectItem value="DONE">Completed</SelectItem>
              <SelectItem value="WONT_DO">Won&apos;t Do</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="w-full sm:w-72">
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search feedback..."
          />
        </div>
      </div>

      {/* Feedback List */}
      {isLoading ? (
        <LoadingTableSkeleton rows={6} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Star}
          title="No feedback submissions found"
          description="All feedback submissions have been processed or none match the active filters."
        />
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {items.map((fb) => (
            <Card key={fb.id} className="rounded-2xl border-border/60 shadow-sm p-6 space-y-4">
              <div className="flex items-start justify-between gap-2">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={`text-xs font-semibold ${
                        fb.type === "BUG"
                          ? "border-rose-500/30 text-rose-600 bg-rose-500/10"
                          : fb.type === "FEATURE"
                          ? "border-primary/30 text-primary bg-primary/10"
                          : "border-amber-500/30 text-amber-600 bg-amber-500/10"
                      }`}
                    >
                      {fb.type}
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                      {fb.status}
                    </Badge>
                    {fb.priority && (
                      <Badge
                        variant="secondary"
                        className={`text-[10px] ${
                          fb.priority === "HIGH" ? "text-rose-600 font-bold" : ""
                        }`}
                      >
                        {fb.priority} Priority
                      </Badge>
                    )}
                  </div>
                  <h3 className="font-semibold text-base text-foreground pt-1">{fb.title}</h3>
                </div>

                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setTriageTarget(fb);
                    setTriageStatus(fb.status);
                    setTriagePriority(fb.priority || "MEDIUM");
                    setAdminNotes(fb.admin_notes || "");
                  }}
                  className="rounded-xl text-xs"
                >
                  Triage
                </Button>
              </div>

              <p className="text-xs text-muted-foreground leading-relaxed whitespace-pre-line">
                {fb.description}
              </p>

              {fb.admin_notes && (
                <div className="p-3 rounded-xl bg-primary/5 border border-primary/20 text-xs">
                  <span className="font-semibold text-primary">Admin Triage Note: </span>
                  <span className="text-foreground">{fb.admin_notes}</span>
                </div>
              )}

              {/* Action items list */}
              {fb.action_items && fb.action_items.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-border/40">
                  <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Action Items ({fb.action_items.length})
                  </span>
                  <div className="space-y-1.5">
                    {fb.action_items.map((act) => (
                      <div
                        key={act.id}
                        onClick={() => handleToggleActionStatus(act)}
                        className="flex items-center justify-between p-2 rounded-lg bg-muted/20 hover:bg-muted/40 cursor-pointer text-xs transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <CheckCircle2
                            className={`size-3.5 ${
                              act.status === "DONE"
                                ? "text-emerald-500 fill-emerald-500/20"
                                : "text-muted-foreground"
                            }`}
                          />
                          <span
                            className={
                              act.status === "DONE"
                                ? "line-through text-muted-foreground"
                                : "text-foreground font-medium"
                            }
                          >
                            {act.title}
                          </span>
                        </div>
                        <Badge variant="outline" className="text-[10px]">
                          {act.status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between pt-3 border-t border-border/40 text-[11px] text-muted-foreground">
                <span>By: {fb.user?.full_name} ({fb.user?.role})</span>
                <span>Submitted {formatRelativeDate(fb.created_at)}</span>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Triage Dialog */}
      <Dialog open={!!triageTarget} onOpenChange={(o) => !o && setTriageTarget(null)}>
        <DialogContent className="rounded-2xl sm:max-w-md">
          <form onSubmit={handleUpdateTriage}>
            <DialogHeader>
              <DialogTitle>Triage Feedback Item</DialogTitle>
              <DialogDescription>
                Update roadmap status and priority for &ldquo;{triageTarget?.title}&rdquo;.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="tStatus">Lifecycle Status</Label>
                  <Select value={triageStatus} onValueChange={(v) => setTriageStatus(v as SystemFeedback["status"])}>
                    <SelectTrigger id="tStatus" className="rounded-xl">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl">
                      <SelectItem value="NEW">New</SelectItem>
                      <SelectItem value="TRIAGED">Triaged</SelectItem>
                      <SelectItem value="PLANNED">Planned</SelectItem>
                      <SelectItem value="IN_PROGRESS">In Progress</SelectItem>
                      <SelectItem value="DONE">Done</SelectItem>
                      <SelectItem value="WONT_DO">Won&apos;t Do</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="tPriority">Priority</Label>
                  <Select value={triagePriority || "MEDIUM"} onValueChange={(v) => setTriagePriority(v as SystemFeedback["priority"])}>
                    <SelectTrigger id="tPriority" className="rounded-xl">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl">
                      <SelectItem value="LOW">Low</SelectItem>
                      <SelectItem value="MEDIUM">Medium</SelectItem>
                      <SelectItem value="HIGH">High</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="tNotes">Internal Admin Notes</Label>
                <Textarea
                  id="tNotes"
                  rows={3}
                  value={adminNotes}
                  onChange={(e) => setAdminNotes(e.target.value)}
                  placeholder="Notes on resolution, target release, or reason for closure..."
                  className="rounded-xl"
                />
              </div>

              {triageTarget && (
                <div className="space-y-2 pt-2 border-t border-border/40">
                  <Label>Assign Action Item</Label>
                  <div className="flex gap-2">
                    <Input
                      value={newActionTitle}
                      onChange={(e) => setNewActionTitle(e.target.value)}
                      placeholder="e.g. Patch validation regex in core"
                      className="rounded-xl text-xs"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => handleAddAction(triageTarget.id)}
                      className="rounded-xl text-xs gap-1"
                    >
                      <Plus className="size-3.5" /> Add
                    </Button>
                  </div>
                </div>
              )}
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setTriageTarget(null)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={updateFeedback.isPending} className="rounded-xl">
                {updateFeedback.isPending ? "Saving..." : "Save Triage"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
