"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingTableSkeleton } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  useCompliancePolicies,
  useViolations,
  useCreatePolicy,
  useUpdatePolicy,
  useUpdateViolation,
  useRunComplianceScan,
} from "@/lib/api/hooks/admin";
import { useDocuments, useVerifyDocument } from "@/lib/api/hooks/documents";
import { formatDate, formatRelativeDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import type { PolicyViolation, ViolationStatus, CompliancePolicy } from "@/lib/api/types-extra";
import type { Document } from "@/lib/api/types";
import {
  ShieldAlert,
  ShieldCheck,
  Play,
  PlusCircle,
  FileCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  ExternalLink,
} from "lucide-react";

export default function AdminCompliancePage() {
  const [tab, setTab] = useState<"violations" | "policies" | "documents">("violations");
  const [violationStatusFilter, setViolationStatusFilter] = useState<string>("ALL");

  const { data: policies, isLoading: isPoliciesLoading, refetch: refetchPolicies } = useCompliancePolicies();
  const { data: violationsData, isLoading: isViolationsLoading, refetch: refetchViolations } = useViolations({
    status: violationStatusFilter !== "ALL" ? (violationStatusFilter as ViolationStatus) : undefined,
    page: 1,
    page_size: 50,
  });
  const { data: pendingDocsData, isLoading: isDocsLoading, refetch: refetchDocs } = useDocuments({
    verification_status: "PENDING",
    page: 1,
    page_size: 50,
  });

  const runScan = useRunComplianceScan();
  const createPolicy = useCreatePolicy();
  const updatePolicy = useUpdatePolicy();
  const updateViolation = useUpdateViolation();
  const verifyDoc = useVerifyDocument();

  // Create Policy Modal State
  const [createPolicyOpen, setCreatePolicyOpen] = useState(false);
  const [polCode, setPolCode] = useState("");
  const [polName, setPolName] = useState("");
  const [polDesc, setPolDesc] = useState("");
  const [polSeverity, setPolSeverity] = useState("HIGH");

  // Update Violation Modal State
  const [violationTarget, setViolationTarget] = useState<PolicyViolation | null>(null);
  const [violStatus, setViolStatus] = useState<ViolationStatus>("RESOLVED");
  const [violNote, setViolNote] = useState("");

  // Document Verification Modal State
  const [docTarget, setDocTarget] = useState<Document | null>(null);
  const [docStatus, setDocStatus] = useState<Document["verification_status"]>("VERIFIED");
  const [docNote, setDocNote] = useState("");

  const violations = violationsData?.items ?? [];
  const pendingDocs = pendingDocsData?.items ?? [];

  const handleRunScan = () => {
    runScan.mutate(undefined, {
      onSuccess: () => {
        toast.success("Institutional compliance scan initiated. Celery worker is running checks.");
        setTimeout(() => refetchViolations(), 2500);
      },
      onError: (err) => toast.error(errorMessage(err, "Failed to initiate compliance scan")),
    });
  };

  const handleCreatePolicy = (e: React.FormEvent) => {
    e.preventDefault();
    if (!polCode || !polName) {
      toast.error("Code and Name are required.");
      return;
    }

    createPolicy.mutate(
      {
        code: polCode.trim().toUpperCase(),
        name: polName.trim(),
        description: polDesc.trim() || undefined,
        severity: polSeverity,
        is_active: true,
      },
      {
        onSuccess: () => {
          toast.success(`Compliance policy ${polCode} created`);
          setCreatePolicyOpen(false);
          setPolCode("");
          setPolName("");
          setPolDesc("");
          refetchPolicies();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to create policy")),
      }
    );
  };

  const handleTogglePolicyActive = (p: CompliancePolicy) => {
    updatePolicy.mutate(
      { id: p.id, body: { is_active: !p.is_active } },
      {
        onSuccess: () => {
          toast.success(`Policy "${p.name}" updated`);
          refetchPolicies();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to update policy status")),
      }
    );
  };

  const handleUpdateViolation = (e: React.FormEvent) => {
    e.preventDefault();
    if (!violationTarget) return;

    updateViolation.mutate(
      { id: violationTarget.id, status: violStatus, note: violNote.trim() || undefined },
      {
        onSuccess: () => {
          toast.success(`Violation status updated to ${violStatus}`);
          setViolationTarget(null);
          refetchViolations();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to update violation")),
      }
    );
  };

  const handleVerifyDocument = (e: React.FormEvent) => {
    e.preventDefault();
    if (!docTarget) return;

    verifyDoc.mutate(
      { id: docTarget.id, verification_status: docStatus, note: docNote.trim() || undefined },
      {
        onSuccess: () => {
          toast.success(`Document marked as ${docStatus}`);
          setDocTarget(null);
          refetchDocs();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to update document verification")),
      }
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Compliance & Institutional Governance"
          description="Enforce accreditation standards, detect placement anomalies, and inspect student verification records."
        />

        <div className="flex items-center gap-2">
          <Button
            onClick={handleRunScan}
            disabled={runScan.isPending}
            className="rounded-xl gap-2 bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            <Play className="size-4 fill-current" />
            {runScan.isPending ? "Scanning..." : "Run Compliance Scan"}
          </Button>
        </div>
      </div>

      <div className="border-b pb-4">
        <Tabs value={tab} onValueChange={(v) => setTab(v as "violations" | "policies" | "documents")}>
          <TabsList className="rounded-xl">
            <TabsTrigger value="violations" className="rounded-lg text-xs gap-1.5">
              <ShieldAlert className="size-3.5" /> Violations ({violations.length})
            </TabsTrigger>
            <TabsTrigger value="policies" className="rounded-lg text-xs gap-1.5">
              <ShieldCheck className="size-3.5" /> Active Policies ({policies?.length || 0})
            </TabsTrigger>
            <TabsTrigger value="documents" className="rounded-lg text-xs gap-1.5">
              <FileCheck className="size-3.5" /> Pending Verification ({pendingDocs.length})
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Tab 1: Violations */}
      {tab === "violations" && (
        <div className="space-y-6">
          <div className="w-48">
            <Select value={violationStatusFilter} onValueChange={setViolationStatusFilter}>
              <SelectTrigger className="rounded-xl">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent className="rounded-xl">
                <SelectItem value="ALL">All Violations</SelectItem>
                <SelectItem value="OPEN">Open Anomalies</SelectItem>
                <SelectItem value="RESOLVED">Resolved</SelectItem>
                <SelectItem value="DISMISSED">Dismissed</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {isViolationsLoading ? (
            <LoadingTableSkeleton rows={5} />
          ) : violations.length === 0 ? (
            <EmptyState
              icon={ShieldCheck}
              title="No compliance violations found"
              description="All institutional placements, documents, and employer criteria are compliant."
            />
          ) : (
            <div className="divide-y divide-border/60 rounded-2xl border border-border/60 bg-card shadow-sm overflow-hidden">
              {violations.map((v) => (
                <div key={v.id} className="flex flex-col sm:flex-row sm:items-center justify-between p-5 gap-4">
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className={`text-xs font-semibold ${
                          v.status === "OPEN"
                            ? "border-rose-500/30 text-rose-600 bg-rose-500/10"
                            : "border-emerald-500/30 text-emerald-600 bg-emerald-500/10"
                        }`}
                      >
                        {v.status}
                      </Badge>
                      <span className="font-mono text-xs font-bold text-foreground">
                        {v.policy_code}
                      </span>
                      <span className="text-xs text-muted-foreground">•</span>
                      <span className="text-xs font-medium text-foreground">
                        Target: {v.entity_type} {v.entity_id ? `(#${v.entity_id.substring(0, 8)})` : ""}
                      </span>
                    </div>

                    <p className="text-xs text-muted-foreground">
                      {v.policy_name || "Institutional Compliance Rule"}
                    </p>

                    {v.details && (
                      <p className="text-xs text-muted-foreground font-mono bg-muted/30 p-2 rounded-lg max-w-2xl">
                        {JSON.stringify(v.details)}
                      </p>
                    )}

                    {v.note && (
                      <p className="text-xs text-foreground bg-primary/5 p-2 rounded-lg border border-primary/20">
                        <strong className="text-primary">Resolution Note: </strong>
                        {v.note}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 self-start sm:self-auto">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setViolationTarget(v);
                        setViolStatus(v.status === "OPEN" ? "RESOLVED" : v.status);
                        setViolNote(v.note || "");
                      }}
                      className="rounded-xl text-xs gap-1.5"
                    >
                      Update Status
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Policies */}
      {tab === "policies" && (
        <div className="space-y-6">
          <div className="flex justify-end">
            <Button onClick={() => setCreatePolicyOpen(true)} className="rounded-xl text-xs gap-2">
              <PlusCircle className="size-4" /> Create Custom Policy
            </Button>
          </div>

          {isPoliciesLoading ? (
            <LoadingTableSkeleton rows={4} />
          ) : !policies || policies.length === 0 ? (
            <EmptyState
              icon={ShieldAlert}
              title="No compliance policies"
              description="No active policies are configured in the system."
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {policies.map((p) => (
                <Card key={p.id} className="rounded-2xl border-border/60 shadow-sm p-5 space-y-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <Badge variant="outline" className="font-mono text-xs font-bold mb-1">
                        {p.code}
                      </Badge>
                      <h3 className="font-semibold text-base text-foreground">{p.name}</h3>
                    </div>
                    <Badge
                      variant="outline"
                      className={`text-xs ${
                        p.severity === "CRITICAL" || p.severity === "HIGH"
                          ? "border-rose-500/30 text-rose-600 bg-rose-500/10"
                          : "border-amber-500/30 text-amber-600 bg-amber-500/10"
                      }`}
                    >
                      {p.severity}
                    </Badge>
                  </div>

                  {p.description && (
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {p.description}
                    </p>
                  )}

                  <div className="flex items-center justify-between pt-3 border-t border-border/40 text-xs">
                    <span className="text-muted-foreground">Enforcement:</span>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-foreground">{p.is_active ? "Enabled" : "Disabled"}</span>
                      <Switch
                        checked={p.is_active}
                        onCheckedChange={() => handleTogglePolicyActive(p)}
                      />
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Document Verification */}
      {tab === "documents" && (
        <div className="space-y-6">
          {isDocsLoading ? (
            <LoadingTableSkeleton rows={4} />
          ) : pendingDocs.length === 0 ? (
            <EmptyState
              icon={FileCheck}
              title="No documents pending verification"
              description="All student resumes, transcripts, and offer letters have been verified."
            />
          ) : (
            <div className="divide-y divide-border/60 rounded-2xl border border-border/60 bg-card shadow-sm overflow-hidden">
              {pendingDocs.map((doc) => (
                <div key={doc.id} className="flex flex-col sm:flex-row sm:items-center justify-between p-4 gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-foreground">{doc.filename}</span>
                      <Badge variant="outline" className="text-xs text-amber-600 bg-amber-500/10">
                        {doc.kind}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Uploaded by: <strong className="text-foreground">{doc.owner?.full_name || "Student"}</strong> • Uploaded {formatRelativeDate(doc.created_at)}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      onClick={() => {
                        setDocTarget(doc);
                        setDocStatus("VERIFIED");
                        setDocNote("");
                      }}
                      className="rounded-xl text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white"
                    >
                      <CheckCircle2 className="size-3.5" /> Verify
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setDocTarget(doc);
                        setDocStatus("REJECTED");
                        setDocNote("");
                      }}
                      className="rounded-xl text-xs text-rose-600 hover:text-rose-700"
                    >
                      <XCircle className="size-3.5" /> Reject
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Create Policy Dialog */}
      <Dialog open={createPolicyOpen} onOpenChange={setCreatePolicyOpen}>
        <DialogContent className="rounded-2xl sm:max-w-md">
          <form onSubmit={handleCreatePolicy}>
            <DialogHeader>
              <DialogTitle>Add Compliance Rule</DialogTitle>
              <DialogDescription>
                Define an automated placement rule or accreditation criterion.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="pCode">Policy Code</Label>
                  <Input
                    id="pCode"
                    value={polCode}
                    onChange={(e) => setPolCode(e.target.value)}
                    placeholder="e.g. POL-007"
                    required
                    className="rounded-xl font-mono text-xs"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pSev">Severity Level</Label>
                  <Select value={polSeverity} onValueChange={setPolSeverity}>
                    <SelectTrigger id="pSev" className="rounded-xl">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl">
                      <SelectItem value="LOW">Low</SelectItem>
                      <SelectItem value="MEDIUM">Medium</SelectItem>
                      <SelectItem value="HIGH">High</SelectItem>
                      <SelectItem value="CRITICAL">Critical</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="pName">Policy Name</Label>
                <Input
                  id="pName"
                  value={polName}
                  onChange={(e) => setPolName(e.target.value)}
                  placeholder="e.g. Minimum Stipend Compliance"
                  required
                  className="rounded-xl"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="pDesc">Policy Description & Rationale</Label>
                <Textarea
                  id="pDesc"
                  rows={3}
                  value={polDesc}
                  onChange={(e) => setPolDesc(e.target.value)}
                  placeholder="Explain when a violation is triggered..."
                  className="rounded-xl"
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreatePolicyOpen(false)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={createPolicy.isPending} className="rounded-xl">
                {createPolicy.isPending ? "Creating..." : "Save Policy"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Update Violation Dialog */}
      <Dialog open={!!violationTarget} onOpenChange={(o) => !o && setViolationTarget(null)}>
        <DialogContent className="rounded-2xl sm:max-w-md">
          <form onSubmit={handleUpdateViolation}>
            <DialogHeader>
              <DialogTitle>Resolve Compliance Anomaly</DialogTitle>
              <DialogDescription>
                Update resolution status for {violationTarget?.policy_code}.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="vStatus">Resolution Status</Label>
                <Select value={violStatus} onValueChange={(v) => setViolStatus(v as ViolationStatus)}>
                  <SelectTrigger id="vStatus" className="rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl">
                    <SelectItem value="OPEN">Open (Requires Action)</SelectItem>
                    <SelectItem value="RESOLVED">Resolved (Issue Fixed)</SelectItem>
                    <SelectItem value="DISMISSED">Dismissed (False Positive / Exception)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="vNote">Resolution Notes</Label>
                <Textarea
                  id="vNote"
                  rows={3}
                  value={violNote}
                  onChange={(e) => setViolNote(e.target.value)}
                  placeholder="Document the corrective action taken or waiver granted..."
                  className="rounded-xl"
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setViolationTarget(null)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={updateViolation.isPending} className="rounded-xl">
                {updateViolation.isPending ? "Updating..." : "Save Resolution"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Verify Document Dialog */}
      <Dialog open={!!docTarget} onOpenChange={(o) => !o && setDocTarget(null)}>
        <DialogContent className="rounded-2xl sm:max-w-md">
          <form onSubmit={handleVerifyDocument}>
            <DialogHeader>
              <DialogTitle>Document Verification Decision</DialogTitle>
              <DialogDescription>
                Review and verify student document: {docTarget?.filename}.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="dStatus">Verification Status</Label>
                <Select value={docStatus} onValueChange={(v) => setDocStatus(v as Document["verification_status"])}>
                  <SelectTrigger id="dStatus" className="rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl">
                    <SelectItem value="VERIFIED">Verified (Approved)</SelectItem>
                    <SelectItem value="REJECTED">Rejected (Invalid / Incomplete)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="dNote">Audit Note</Label>
                <Textarea
                  id="dNote"
                  rows={3}
                  value={docNote}
                  onChange={(e) => setDocNote(e.target.value)}
                  placeholder="Notes on credentials or reason for rejection..."
                  className="rounded-xl"
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDocTarget(null)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={verifyDoc.isPending} className="rounded-xl">
                {verifyDoc.isPending ? "Confirming..." : "Submit Decision"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
