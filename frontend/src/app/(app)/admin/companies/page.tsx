"use client";

import { useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/shared/PageHeader";
import { SearchInput } from "@/components/shared/SearchInput";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingTableSkeleton } from "@/components/shared/LoadingSkeletons";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  useCompanies,
  useApproveCompany,
  useArchiveCompany,
  useRestoreCompany,
  useDeleteCompany,
  useCompanyMembers,
  useCreateCompany,
} from "@/lib/api/hooks/companies";
import { formatDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import type { CompanyStatus, CompanySummary } from "@/lib/api/types";
import {
  Building2,
  PlusCircle,
  CheckCircle2,
  Archive,
  RefreshCw,
  Trash2,
  Users,
  ExternalLink,
  ShieldCheck,
  Star,
  MapPin,
  Globe,
} from "lucide-react";

export default function AdminCompaniesPage() {
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [search, setSearch] = useState("");

  const { data, isLoading, refetch } = useCompanies({
    status: statusFilter !== "ALL" ? (statusFilter as CompanyStatus) : undefined,
    q: search || undefined,
    page: 1,
    page_size: 50,
  });

  const approveCompany = useApproveCompany();
  const archiveCompany = useArchiveCompany();
  const restoreCompany = useRestoreCompany();
  const deleteCompany = useDeleteCompany();
  const createCompany = useCreateCompany();

  // Create Company Dialog State
  const [createOpen, setCreateOpen] = useState(false);
  const [cName, setCName] = useState("");
  const [cRegNo, setCRegNo] = useState("");
  const [cLocation, setCLocation] = useState("");
  const [cIndustry, setCIndustry] = useState("");
  const [cWebsite, setCWebsite] = useState("");
  const [cPocName, setCPocName] = useState("");
  const [cPocEmail, setCPocEmail] = useState("");
  const [cPocPhone, setCPocPhone] = useState("");

  // Members Dialog
  const [membersTarget, setMembersTarget] = useState<CompanySummary | null>(null);
  const { data: membersList, isLoading: isMembersLoading } = useCompanyMembers(
    membersTarget?.id,
    !!membersTarget
  );

  // Delete Target Dialog
  const [deleteTarget, setDeleteTarget] = useState<CompanySummary | null>(null);

  const companies = (data?.items ?? []).filter((c) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      c.name.toLowerCase().includes(q) ||
      c.location?.toLowerCase().includes(q) ||
      c.registration_number?.toLowerCase().includes(q)
    );
  });

  const handleApprove = (id: string, name: string) => {
    approveCompany.mutate(id, {
      onSuccess: () => {
        toast.success(`Company "${name}" verified and approved`);
        refetch();
      },
      onError: (err) => toast.error(errorMessage(err, "Failed to approve company")),
    });
  };

  const handleArchive = (id: string, name: string) => {
    archiveCompany.mutate(id, {
      onSuccess: () => {
        toast.info(`Company "${name}" archived`);
        refetch();
      },
      onError: (err) => toast.error(errorMessage(err, "Failed to archive company")),
    });
  };

  const handleRestore = (id: string, name: string) => {
    restoreCompany.mutate(id, {
      onSuccess: () => {
        toast.success(`Company "${name}" restored`);
        refetch();
      },
      onError: (err) => toast.error(errorMessage(err, "Failed to restore company")),
    });
  };

  const handleDelete = () => {
    if (!deleteTarget) return;
    deleteCompany.mutate(deleteTarget.id, {
      onSuccess: () => {
        toast.success(`Company "${deleteTarget.name}" deleted`);
        setDeleteTarget(null);
        refetch();
      },
      onError: (err) => toast.error(errorMessage(err, "Failed to delete company")),
    });
  };

  const handleCreateCompany = (e: React.FormEvent) => {
    e.preventDefault();
    if (!cName || !cRegNo || !cLocation || !cPocName || !cPocEmail) {
      toast.error("Please fill in company name, registration number, location, and contact POC details.");
      return;
    }

    createCompany.mutate(
      {
        name: cName.trim(),
        registration_number: cRegNo.trim(),
        location: cLocation.trim(),
        industry: cIndustry.trim() || undefined,
        website: cWebsite.trim() || undefined,
        contact_person_name: cPocName.trim(),
        contact_email: cPocEmail.trim(),
        contact_phone: cPocPhone.trim() || undefined,
      },
      {
        onSuccess: () => {
          toast.success(`Company "${cName}" registered`);
          setCreateOpen(false);
          // reset form
          setCName("");
          setCRegNo("");
          setCLocation("");
          refetch();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to register company")),
      }
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Corporate Partners & Employers"
          description="Manage corporate partner verification, view recruiter affiliations, and oversee enterprise profiles."
        />

        <Button onClick={() => setCreateOpen(true)} className="rounded-xl gap-2">
          <PlusCircle className="size-4" /> Register Employer
        </Button>
      </div>

      {/* Filters and Search Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="w-48">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="rounded-xl">
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent className="rounded-xl">
              <SelectItem value="ALL">All Companies ({data?.total ?? 0})</SelectItem>
              <SelectItem value="ACTIVE">Active / Verified</SelectItem>
              <SelectItem value="PENDING">Pending Verification</SelectItem>
              <SelectItem value="ARCHIVED">Archived</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="w-full sm:w-72">
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search company or CIN..."
          />
        </div>
      </div>

      {/* Companies List */}
      {isLoading ? (
        <LoadingTableSkeleton rows={6} />
      ) : companies.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="No companies found"
          description="No registered companies match your filter criteria."
          action={
            <Button onClick={() => setCreateOpen(true)} className="rounded-xl">
              Register First Employer
            </Button>
          }
        />
      ) : (
        <div className="divide-y divide-border/60 rounded-2xl border border-border/60 bg-card shadow-sm overflow-hidden">
          {companies.map((c) => (
            <div
              key={c.id}
              className="flex flex-col gap-4 p-5 transition-colors hover:bg-muted/20 lg:flex-row lg:items-center lg:justify-between"
            >
              <div className="flex items-start gap-4">
                <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold shadow-xs">
                  {c.name?.[0]?.toUpperCase() || <Building2 className="size-6" />}
                </div>

                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Link
                      href={`/companies/${c.id}`}
                      className="font-semibold text-base text-foreground hover:text-primary transition-colors flex items-center gap-1.5"
                    >
                      {c.name} <ExternalLink className="size-3 text-muted-foreground" />
                    </Link>
                    <Badge
                      variant="outline"
                      className={`text-xs font-semibold ${
                        c.status === "ACTIVE"
                          ? "border-emerald-500/20 text-emerald-600 bg-emerald-500/10"
                          : c.status === "PENDING"
                          ? "border-amber-500/20 text-amber-600 bg-amber-500/10"
                          : "border-zinc-500/20 text-zinc-500 bg-zinc-500/10"
                      }`}
                    >
                      {c.status}
                    </Badge>
                  </div>

                  <p className="text-xs text-muted-foreground flex items-center gap-2">
                    <span>CIN: {c.registration_number}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <MapPin className="size-3" /> {c.location}
                    </span>
                    {c.industry && (
                      <>
                        <span>•</span>
                        <span>{c.industry}</span>
                      </>
                    )}
                  </p>

                  <div className="flex items-center gap-3 text-xs text-muted-foreground pt-1">
                    <span className="flex items-center gap-1 font-semibold text-amber-600">
                      <Star className="size-3 fill-current" /> {c.avg_rating?.toFixed(1) || "5.0"} ({c.rating_count || 0} reviews)
                    </span>
                    <span>•</span>
                    <span>{c.open_internships || 0} Open Postings</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-2 self-start lg:self-center">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setMembersTarget(c)}
                  className="rounded-xl text-xs gap-1.5"
                >
                  <Users className="size-3.5 text-primary" /> Members
                </Button>

                {c.status === "PENDING" && (
                  <Button
                    size="sm"
                    onClick={() => handleApprove(c.id, c.name)}
                    disabled={approveCompany.isPending}
                    className="rounded-xl text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white"
                  >
                    <CheckCircle2 className="size-3.5" /> Approve
                  </Button>
                )}

                {c.status === "ACTIVE" && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleArchive(c.id, c.name)}
                    disabled={archiveCompany.isPending}
                    className="rounded-xl text-xs gap-1 text-muted-foreground hover:text-amber-600"
                  >
                    <Archive className="size-3.5" /> Archive
                  </Button>
                )}

                {c.status === "ARCHIVED" && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleRestore(c.id, c.name)}
                    disabled={restoreCompany.isPending}
                    className="rounded-xl text-xs gap-1 text-primary"
                  >
                    <RefreshCw className="size-3.5" /> Restore
                  </Button>
                )}

                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setDeleteTarget(c)}
                  className="rounded-xl text-xs text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Register Partner Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="rounded-2xl sm:max-w-md max-h-[85vh] overflow-y-auto">
          <form onSubmit={handleCreateCompany}>
            <DialogHeader>
              <DialogTitle>Register Corporate Partner</DialogTitle>
              <DialogDescription>
                Add a new verified employer entity to the CampusHire network.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="regName">Company Name</Label>
                <Input
                  id="regName"
                  value={cName}
                  onChange={(e) => setCName(e.target.value)}
                  placeholder="e.g. Apex Robotics"
                  required
                  className="rounded-xl"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="regCin">Registration / CIN</Label>
                  <Input
                    id="regCin"
                    value={cRegNo}
                    onChange={(e) => setCRegNo(e.target.value)}
                    placeholder="U72200..."
                    required
                    className="rounded-xl font-mono text-xs"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="regLoc">Headquarters</Label>
                  <Input
                    id="regLoc"
                    value={cLocation}
                    onChange={(e) => setCLocation(e.target.value)}
                    placeholder="Bengaluru"
                    required
                    className="rounded-xl"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="regInd">Industry</Label>
                  <Input
                    id="regInd"
                    value={cIndustry}
                    onChange={(e) => setCIndustry(e.target.value)}
                    placeholder="Software / AI"
                    className="rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="regWeb">Website</Label>
                  <Input
                    id="regWeb"
                    type="url"
                    value={cWebsite}
                    onChange={(e) => setCWebsite(e.target.value)}
                    placeholder="https://..."
                    className="rounded-xl"
                  />
                </div>
              </div>

              <div className="border-t border-border/40 pt-3 space-y-3">
                <h4 className="text-xs font-semibold uppercase text-muted-foreground">
                  Primary Contact Person
                </h4>
                <div className="space-y-2">
                  <Label htmlFor="regPoc">POC Name</Label>
                  <Input
                    id="regPoc"
                    value={cPocName}
                    onChange={(e) => setCPocName(e.target.value)}
                    placeholder="Recruiter Name"
                    required
                    className="rounded-xl"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label htmlFor="regPocEmail">POC Email</Label>
                    <Input
                      id="regPocEmail"
                      type="email"
                      value={cPocEmail}
                      onChange={(e) => setCPocEmail(e.target.value)}
                      placeholder="hr@example.com"
                      required
                      className="rounded-xl"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="regPocPhone">POC Phone</Label>
                    <Input
                      id="regPocPhone"
                      value={cPocPhone}
                      onChange={(e) => setCPocPhone(e.target.value)}
                      placeholder="+91..."
                      className="rounded-xl"
                    />
                  </div>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={createCompany.isPending} className="rounded-xl">
                {createCompany.isPending ? "Registering..." : "Register Partner"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Members Dialog */}
      <Dialog open={!!membersTarget} onOpenChange={(o) => !o && setMembersTarget(null)}>
        <DialogContent className="rounded-2xl sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Recruiter Members — {membersTarget?.name}</DialogTitle>
            <DialogDescription>
              User accounts authorized to recruit for this company.
            </DialogDescription>
          </DialogHeader>

          <div className="py-4 space-y-2 max-h-60 overflow-y-auto">
            {isMembersLoading ? (
              <p className="text-xs text-muted-foreground text-center py-4">Loading members...</p>
            ) : !membersList || membersList.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-4">No recruiters affiliated with this company yet.</p>
            ) : (
              membersList.map((m) => (
                <div key={m.user_id} className="flex items-center justify-between p-3 rounded-xl border border-border/40 text-xs">
                  <div>
                    <h5 className="font-semibold text-foreground">{m.full_name}</h5>
                    <p className="text-muted-foreground">{m.email}</p>
                  </div>
                  <Badge variant="secondary">{m.job_title || "Recruiter"}</Badge>
                </div>
              ))
            )}
          </div>

          <DialogFooter>
            <Button onClick={() => setMembersTarget(null)} className="rounded-xl text-xs">
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
        title={`Delete ${deleteTarget?.name}?`}
        description="Permanently delete this company entity from the platform? This cannot be undone."
        confirmText="Delete Company"
        variant="destructive"
        onConfirm={handleDelete}
      />
    </div>
  );
}
