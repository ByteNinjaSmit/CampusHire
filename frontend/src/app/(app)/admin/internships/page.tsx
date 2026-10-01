"use client";

import { useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { SearchInput } from "@/components/shared/SearchInput";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingTableSkeleton } from "@/components/shared/LoadingSkeletons";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  useInternships,
  useApproveInternship,
  useRejectInternship,
  useArchiveInternship,
  useCloseInternship,
  useBulkInternships,
} from "@/lib/api/hooks/internships";
import { formatCurrency, formatDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import type { Internship, InternshipStatus } from "@/lib/api/types";
import {
  Briefcase,
  Building2,
  CheckCircle2,
  XCircle,
  Archive,
  ExternalLink,
  Users,
  AlertCircle,
  Eye,
} from "lucide-react";

export default function AdminInternshipsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [search, setSearch] = useState("");

  const { data, isLoading, refetch } = useInternships({
    status: statusFilter !== "ALL" ? (statusFilter as InternshipStatus) : undefined,
    page: 1,
    page_size: 50,
  });

  const approveInternship = useApproveInternship();
  const rejectInternship = useRejectInternship();
  const closeInternship = useCloseInternship();
  const archiveInternship = useArchiveInternship();
  const bulkInternships = useBulkInternships();

  // Reject dialog state
  const [rejectTarget, setRejectTarget] = useState<Internship | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  // Bulk selection
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const postings = (data?.items ?? []).filter((item) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      item.title.toLowerCase().includes(q) ||
      item.company?.name?.toLowerCase().includes(q) ||
      item.domain.toLowerCase().includes(q)
    );
  });

  const pendingApprovalPostings = postings.filter((p) => p.status === "PENDING_APPROVAL");

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(postings.map((p) => p.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const handleApprove = (id: string, title: string) => {
    approveInternship.mutate(id, {
      onSuccess: () => {
        toast.success(`Posting "${title}" approved!`);
        refetch();
      },
      onError: (err) => toast.error(errorMessage(err, "Failed to approve internship")),
    });
  };

  const handleReject = (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectTarget) return;

    rejectInternship.mutate(
      { id: rejectTarget.id, reason: rejectReason.trim() || "Does not comply with placement policy." },
      {
        onSuccess: () => {
          toast.info(`Posting rejected`);
          setRejectTarget(null);
          setRejectReason("");
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to reject posting")),
      }
    );
  };

  const handleBulkApprove = () => {
    if (selectedIds.length === 0) return;
    bulkInternships.mutate(
      { ids: selectedIds, action: "approve" },
      {
        onSuccess: () => {
          toast.success(`Approved ${selectedIds.length} internships`);
          setSelectedIds([]);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Bulk approve failed")),
      }
    );
  };

  const handleBulkReject = () => {
    if (selectedIds.length === 0) return;
    bulkInternships.mutate(
      { ids: selectedIds, action: "reject", reason: "Administrative bulk rejection" },
      {
        onSuccess: () => {
          toast.info(`Rejected ${selectedIds.length} internships`);
          setSelectedIds([]);
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Bulk reject failed")),
      }
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Campus Internship Postings Oversight"
          description="Screen submitted opportunities, review eligibility criteria, and manage active placement drives."
        />
      </div>

      {/* Pending Queue Highlight */}
      {pendingApprovalPostings.length > 0 && statusFilter === "ALL" && (
        <Card className="rounded-2xl border-amber-500/30 bg-amber-500/5 shadow-xs overflow-hidden">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
              <AlertCircle className="size-5" />
              <div>
                <CardTitle className="text-base font-semibold">
                  Awaiting Administrative Approval ({pendingApprovalPostings.length})
                </CardTitle>
                <CardDescription className="text-xs text-amber-700/80 dark:text-amber-400/80">
                  These postings are pending screening before becoming visible to students.
                </CardDescription>
              </div>
            </div>
            {selectedIds.length > 0 && (
              <div className="flex items-center gap-2">
                <Button size="sm" onClick={handleBulkApprove} className="rounded-xl text-xs gap-1 bg-emerald-600 hover:bg-emerald-700 text-white">
                  <CheckCircle2 className="size-3.5" /> Approve Selected ({selectedIds.length})
                </Button>
                <Button size="sm" variant="outline" onClick={handleBulkReject} className="rounded-xl text-xs gap-1 text-rose-600 hover:text-rose-700">
                  <XCircle className="size-3.5" /> Reject Selected
                </Button>
              </div>
            )}
          </CardHeader>
          <CardContent className="divide-y divide-amber-500/20 p-0">
            {pendingApprovalPostings.map((p) => (
              <div key={p.id} className="flex flex-col sm:flex-row sm:items-center justify-between p-4 gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-foreground">{p.title}</span>
                    <Badge variant="secondary" className="text-[10px]">
                      {p.domain}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    By: <strong className="text-foreground">{p.company?.name}</strong> • Stipend: ₹{p.stipend_monthly}/mo • {p.duration_weeks} Weeks
                  </p>
                </div>

                <div className="flex items-center gap-2 self-start sm:self-auto">
                  <Button size="sm" asChild variant="outline" className="rounded-xl text-xs gap-1">
                    <Link href={`/internships/${p.id}`} target="_blank">
                      <Eye className="size-3.5" /> Inspect
                    </Link>
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => handleApprove(p.id, p.title)}
                    disabled={approveInternship.isPending}
                    className="rounded-xl text-xs gap-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                  >
                    <CheckCircle2 className="size-3.5" /> Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setRejectTarget(p);
                      setRejectReason("");
                    }}
                    className="rounded-xl text-xs text-rose-600 hover:text-rose-700"
                  >
                    <XCircle className="size-3.5" /> Reject
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Filters and Search Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-48 rounded-xl">
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent className="rounded-xl">
              <SelectItem value="ALL">All Statuses ({data?.total ?? 0})</SelectItem>
              <SelectItem value="PENDING_APPROVAL">Pending Approval</SelectItem>
              <SelectItem value="APPROVED">Active / Approved</SelectItem>
              <SelectItem value="DRAFT">Draft</SelectItem>
              <SelectItem value="CLOSED">Closed</SelectItem>
              <SelectItem value="REJECTED">Rejected</SelectItem>
            </SelectContent>
          </Select>

          {selectedIds.length > 0 && (
            <div className="flex items-center gap-2 rounded-xl bg-muted/60 px-3 py-1 text-xs">
              <span className="font-semibold text-foreground">{selectedIds.length} selected</span>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleBulkApprove}
                className="h-7 text-xs text-emerald-600 hover:text-emerald-700"
              >
                Approve
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleBulkReject}
                className="h-7 text-xs text-rose-600 hover:text-rose-700"
              >
                Reject
              </Button>
            </div>
          )}
        </div>

        <div className="w-full sm:w-72">
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search posting, company, or domain..."
          />
        </div>
      </div>

      {/* Internships List */}
      {isLoading ? (
        <LoadingTableSkeleton rows={6} />
      ) : postings.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          title="No internships found"
          description="No postings match your current filter."
        />
      ) : (
        <div className="divide-y divide-border/60 rounded-2xl border border-border/60 bg-card shadow-sm overflow-hidden">
          {postings.map((item) => {
            const isSelected = selectedIds.includes(item.id);
            return (
              <div
                key={item.id}
                className={`flex flex-col gap-4 p-5 transition-colors lg:flex-row lg:items-center lg:justify-between ${
                  isSelected ? "bg-primary/5" : "hover:bg-muted/20"
                }`}
              >
                <div className="flex items-start gap-3.5">
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={() => handleToggleSelect(item.id)}
                    aria-label={`Select ${item.title}`}
                    className="mt-1"
                  />
                  <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold shadow-xs">
                    {item.company?.name?.[0]?.toUpperCase() || <Building2 className="size-6" />}
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-muted-foreground uppercase">
                        {item.company?.name || "Corporate Partner"}
                      </span>
                      <StatusBadge status={item.status} />
                    </div>

                    <h3 className="font-semibold text-base text-foreground hover:text-primary transition-colors">
                      <Link href={`/internships/${item.id}`}>{item.title}</Link>
                    </h3>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                      <Badge variant="secondary" className="text-[10px]">
                        {item.work_mode}
                      </Badge>
                      <span>{item.domain}</span>
                      <span>•</span>
                      <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                        {item.stipend_monthly ? `${formatCurrency(item.stipend_monthly)} / mo` : "Unpaid"}
                      </span>
                      <span>•</span>
                      <span>Deadline: {formatDate(item.application_deadline)}</span>
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 self-start lg:self-center pl-7 lg:pl-0">
                  <Button size="sm" asChild variant="outline" className="rounded-xl text-xs gap-1.5">
                    <Link href={`/internships/${item.id}`}>
                      <Eye className="size-3.5" /> View Posting
                    </Link>
                  </Button>

                  {item.status === "PENDING_APPROVAL" && (
                    <>
                      <Button
                        size="sm"
                        onClick={() => handleApprove(item.id, item.title)}
                        disabled={approveInternship.isPending}
                        className="rounded-xl text-xs gap-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                      >
                        <CheckCircle2 className="size-3.5" /> Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setRejectTarget(item);
                          setRejectReason("");
                        }}
                        className="rounded-xl text-xs text-rose-600 hover:text-rose-700"
                      >
                        <XCircle className="size-3.5" /> Reject
                      </Button>
                    </>
                  )}

                  {item.status === "APPROVED" && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => closeInternship.mutate(item.id, { onSuccess: () => { toast.info("Posting closed"); refetch(); } })}
                      className="rounded-xl text-xs text-amber-600 hover:text-amber-700"
                    >
                      Close Posting
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Reject Reason Dialog */}
      <Dialog open={!!rejectTarget} onOpenChange={(o) => !o && setRejectTarget(null)}>
        <DialogContent className="rounded-2xl sm:max-w-md">
          <form onSubmit={handleReject}>
            <DialogHeader>
              <DialogTitle>Reject Internship Posting</DialogTitle>
              <DialogDescription>
                Provide the rejection rationale for &ldquo;{rejectTarget?.title}&rdquo;.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="rejReason">Rejection Feedback</Label>
                <Textarea
                  id="rejReason"
                  rows={3}
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="e.g. Inadequate stipend, missing course prerequisites, or invalid start date..."
                  required
                  className="rounded-xl"
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setRejectTarget(null)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" variant="destructive" disabled={rejectInternship.isPending} className="rounded-xl">
                {rejectInternship.isPending ? "Rejecting..." : "Confirm Rejection"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
