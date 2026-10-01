"use client";

import { useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { SearchInput } from "@/components/shared/SearchInput";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { LoadingTableSkeleton } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  useInternships,
  useSubmitInternship,
  useArchiveInternship,
  useCloseInternship,
} from "@/lib/api/hooks/internships";
import { useAuth } from "@/providers/AuthProvider";
import { formatCurrency, formatDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import type { InternshipStatus } from "@/lib/api/types";
import {
  Briefcase,
  Building2,
  PlusCircle,
  Users,
  Edit,
  Send,
  Archive,
} from "lucide-react";

export default function CompanyInternshipsPage() {
  const { user } = useAuth();
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [search, setSearch] = useState("");
  const [archiveTargetId, setArchiveTargetId] = useState<string | null>(null);

  const companyId = user?.company?.company_id;

  const { data, isLoading, refetch } = useInternships({
    company_id: companyId,
    posted_by: !companyId ? user?.id : undefined,
    status: statusFilter !== "ALL" ? (statusFilter as InternshipStatus) : undefined,
    page: 1,
    page_size: 50,
  });

  const submitInternship = useSubmitInternship();
  const archiveInternship = useArchiveInternship();
  const closeInternship = useCloseInternship();

  const postings = (data?.items ?? []).filter((item) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      item.title.toLowerCase().includes(q) ||
      item.domain.toLowerCase().includes(q) ||
      item.location.toLowerCase().includes(q)
    );
  });

  const handleSubmitForApproval = (id: string) => {
    submitInternship.mutate(id, {
      onSuccess: () => {
        toast.success("Submitted for administrative approval");
        refetch();
      },
      onError: (err) => toast.error(errorMessage(err, "Failed to submit posting")),
    });
  };

  const handleArchive = () => {
    if (!archiveTargetId) return;
    archiveInternship.mutate(archiveTargetId, {
      onSuccess: () => {
        toast.success("Posting archived");
        setArchiveTargetId(null);
        refetch();
      },
      onError: (err) => toast.error(errorMessage(err, "Failed to archive posting")),
    });
  };

  const handleClose = (id: string) => {
    closeInternship.mutate(id, {
      onSuccess: () => {
        toast.success("Posting closed to new applicants");
        refetch();
      },
      onError: (err) => toast.error(errorMessage(err, "Failed to close posting")),
    });
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Company Internship Postings"
          description="Manage corporate internship opportunities, review applicants, and track candidate hiring stages."
        />
        <Button asChild className="gap-2 rounded-xl">
          <Link href="/company/internships/new">
            <PlusCircle className="size-4" /> Create New Posting
          </Link>
        </Button>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="w-48">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="rounded-xl">
              <SelectValue placeholder="Status Filter" />
            </SelectTrigger>
            <SelectContent className="rounded-xl">
              <SelectItem value="ALL">All Statuses ({data?.total ?? 0})</SelectItem>
              <SelectItem value="DRAFT">Draft</SelectItem>
              <SelectItem value="PENDING_APPROVAL">Pending Approval</SelectItem>
              <SelectItem value="APPROVED">Active / Approved</SelectItem>
              <SelectItem value="CLOSED">Closed</SelectItem>
              <SelectItem value="REJECTED">Rejected</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="w-full sm:w-72">
          <SearchInput value={search} onChange={setSearch} placeholder="Search postings..." />
        </div>
      </div>

      {isLoading ? (
        <LoadingTableSkeleton rows={5} />
      ) : postings.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          title="No postings found"
          description={
            statusFilter !== "ALL"
              ? `No postings found with status "${statusFilter}".`
              : "Your company hasn't posted any internships yet."
          }
          action={
            <Button asChild className="rounded-xl">
              <Link href="/company/internships/new">Create Your First Posting</Link>
            </Button>
          }
        />
      ) : (
        <div className="divide-y divide-border/60 rounded-2xl border border-border/60 bg-card shadow-sm">
          {postings.map((item) => (
            <div
              key={item.id}
              className="flex flex-col gap-4 p-5 transition-colors hover:bg-muted/30 lg:flex-row lg:items-center lg:justify-between"
            >
              <div className="flex items-start gap-4">
                <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold shadow-xs">
                  {item.company?.name?.[0]?.toUpperCase() || <Building2 className="size-6" />}
                </div>

                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-muted-foreground uppercase">
                      {item.company?.name || user?.company?.company_name || "Company Posting"}
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
                    <span>{item.duration_weeks} Weeks</span>
                    <span>•</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                      {item.stipend_monthly ? `${formatCurrency(item.stipend_monthly)} / mo` : "Unpaid"}
                    </span>
                    <span>•</span>
                    <span>Deadline: {formatDate(item.application_deadline)}</span>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 self-start lg:self-center">
                <Button size="sm" asChild variant="default" className="rounded-xl text-xs gap-1.5">
                  <Link href={`/company/review/${item.id}`}>
                    <Users className="size-3.5" /> Review Applicants
                  </Link>
                </Button>

                {item.status === "DRAFT" && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleSubmitForApproval(item.id)}
                    disabled={submitInternship.isPending}
                    className="rounded-xl text-xs gap-1.5"
                  >
                    <Send className="size-3.5 text-primary" /> Submit for Approval
                  </Button>
                )}

                {item.status === "APPROVED" && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleClose(item.id)}
                    disabled={closeInternship.isPending}
                    className="rounded-xl text-xs text-amber-600 hover:text-amber-700"
                  >
                    Close Posting
                  </Button>
                )}

                <Button size="sm" asChild variant="outline" className="rounded-xl text-xs gap-1.5">
                  <Link href={`/company/internships/${item.id}/edit`}>
                    <Edit className="size-3.5" /> Edit
                  </Link>
                </Button>

                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setArchiveTargetId(item.id)}
                  className="rounded-xl text-xs text-muted-foreground hover:text-destructive"
                >
                  <Archive className="size-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={!!archiveTargetId}
        onOpenChange={(o) => !o && setArchiveTargetId(null)}
        title="Archive Posting"
        description="Are you sure you want to archive this internship? It will be removed from student view."
        confirmText="Archive"
        variant="destructive"
        onConfirm={handleArchive}
      />
    </div>
  );
}
