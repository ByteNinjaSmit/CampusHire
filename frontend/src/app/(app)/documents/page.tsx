"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { FileUpload } from "@/components/shared/FileUpload";
import { PdfViewer } from "@/components/shared/PdfViewer";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingTableSkeleton } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useDocuments, useDeleteDocument } from "@/lib/api/hooks/documents";
import { useMyStudentProfile, useSetDefaultResume } from "@/lib/api/hooks/students";
import { useAuth } from "@/providers/AuthProvider";
import { formatBytes, formatRelativeDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import type { Document, DocumentKind } from "@/lib/api/types";
import {
  FileText,
  Trash2,
  Eye,
  CheckCircle,
  Clock,
  XCircle,
  Star,
  Download,
  Upload,
} from "lucide-react";

export default function DocumentsPage() {
  const { user } = useAuth();
  const isStudent = user?.role === "STUDENT";

  const [kindFilter, setKindFilter] = useState<string>("ALL");
  const [previewDoc, setPreviewDoc] = useState<Document | null>(null);
  const [deleteDocId, setDeleteDocId] = useState<string | null>(null);
  const [selectedUploadKind, setSelectedUploadKind] = useState<DocumentKind>("RESUME");

  const { data, isLoading, refetch } = useDocuments({
    kind: kindFilter !== "ALL" ? (kindFilter as DocumentKind) : undefined,
    page: 1,
    page_size: 50,
  });

  const { data: studentProfile } = useMyStudentProfile(isStudent);
  const setDefaultResume = useSetDefaultResume();
  const deleteDoc = useDeleteDocument();

  const documents = data?.items ?? [];

  const handleSetDefault = (id: string) => {
    setDefaultResume.mutate(id, {
      onSuccess: () => toast.success("Set as default application resume"),
      onError: (err) => toast.error(errorMessage(err, "Failed to set default resume")),
    });
  };

  const handleDelete = () => {
    if (!deleteDocId) return;
    deleteDoc.mutate(deleteDocId, {
      onSuccess: () => {
        toast.success("Document deleted");
        setDeleteDocId(null);
      },
      onError: (err) => toast.error(errorMessage(err, "Failed to delete document")),
    });
  };

  const getVerificationBadge = (status: string) => {
    switch (status) {
      case "VERIFIED":
        return (
          <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 gap-1 border-emerald-500/20">
            <CheckCircle className="size-3" /> Verified
          </Badge>
        );
      case "REJECTED":
        return (
          <Badge className="bg-rose-500/10 text-rose-600 dark:text-rose-400 gap-1 border-rose-500/20">
            <XCircle className="size-3" /> Rejected
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="gap-1 text-amber-600 dark:text-amber-400 border-amber-500/20">
            <Clock className="size-3" /> Pending Verification
          </Badge>
        );
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Documents Center"
        description="Upload and manage your resumes, offer letters, and institutional documents."
      />

      {/* Upload Box */}
      <Card className="rounded-2xl border-border/60 shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-lg">Upload New Document</CardTitle>
            <CardDescription>
              Upload PDF documents up to 5 MB. PDF signature is validated automatically.
            </CardDescription>
          </div>
          <div className="w-44">
            <Select
              value={selectedUploadKind}
              onValueChange={(v) => setSelectedUploadKind(v as DocumentKind)}
            >
              <SelectTrigger className="rounded-xl">
                <SelectValue placeholder="Document Kind" />
              </SelectTrigger>
              <SelectContent className="rounded-xl">
                <SelectItem value="RESUME">Resume</SelectItem>
                <SelectItem value="OFFER_LETTER">Offer Letter</SelectItem>
                <SelectItem value="REPORT">Report</SelectItem>
                <SelectItem value="OTHER">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <FileUpload
            kind={selectedUploadKind}
            label={`Upload ${selectedUploadKind.replace("_", " ").toLowerCase()}`}
            hint="Drag and drop your PDF here, or click to browse (Max 5 MB)"
            onUploaded={(doc) => {
              toast.success(`"${doc.file_name}" uploaded successfully`);
              refetch();
            }}
          />
        </CardContent>
      </Card>

      {/* Documents List */}
      <Card className="rounded-2xl border-border/60 shadow-sm">
        <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-lg">My Documents</CardTitle>
            <CardDescription>All uploaded files associated with your account.</CardDescription>
          </div>
          <div className="w-40">
            <Select value={kindFilter} onValueChange={setKindFilter}>
              <SelectTrigger className="rounded-xl">
                <SelectValue placeholder="Filter by kind" />
              </SelectTrigger>
              <SelectContent className="rounded-xl">
                <SelectItem value="ALL">All Documents</SelectItem>
                <SelectItem value="RESUME">Resumes</SelectItem>
                <SelectItem value="OFFER_LETTER">Offer Letters</SelectItem>
                <SelectItem value="REPORT">Reports</SelectItem>
                <SelectItem value="OTHER">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <LoadingTableSkeleton rows={4} />
          ) : documents.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No documents found"
              description="Upload your resume or other documents above to get started."
            />
          ) : (
            <div className="divide-y divide-border/60 rounded-xl border border-border/60">
              {documents.map((doc) => {
                const isDefault = isStudent && studentProfile?.default_resume_id === doc.id;
                return (
                  <div
                    key={doc.id}
                    className="flex flex-col gap-3 p-4 transition-colors hover:bg-muted/30 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                        <FileText className="size-5" />
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium text-sm text-foreground">{doc.file_name}</h4>
                          {isDefault && (
                            <Badge className="bg-primary/10 text-primary border-primary/20 text-xs">
                              Default Resume
                            </Badge>
                          )}
                        </div>
                        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                          <Badge variant="secondary" className="text-[10px]">
                            {doc.kind}
                          </Badge>
                          <span>{formatBytes(doc.file_size_bytes)}</span>
                          <span>•</span>
                          <span>Uploaded {formatRelativeDate(doc.created_at)}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 self-start sm:self-center">
                      {getVerificationBadge(doc.verification_status)}

                      {isStudent && doc.kind === "RESUME" && !isDefault && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleSetDefault(doc.id)}
                          disabled={setDefaultResume.isPending}
                          className="h-8 gap-1.5 rounded-lg text-xs"
                        >
                          <Star className="size-3.5" /> Set Default
                        </Button>
                      )}

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPreviewDoc(doc)}
                        className="h-8 gap-1.5 rounded-lg text-xs"
                      >
                        <Eye className="size-3.5" /> Preview
                      </Button>

                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8 text-muted-foreground hover:text-destructive"
                        onClick={() => setDeleteDocId(doc.id)}
                        title="Delete"
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* PDF Preview Dialog */}
      <Dialog open={!!previewDoc} onOpenChange={(open) => !open && setPreviewDoc(null)}>
        <DialogContent className="max-w-4xl rounded-2xl p-6">
          <DialogHeader>
            <DialogTitle>{previewDoc?.file_name}</DialogTitle>
            <DialogDescription>
              {previewDoc?.kind} • {previewDoc && formatBytes(previewDoc.file_size_bytes)}
            </DialogDescription>
          </DialogHeader>
          {previewDoc && <PdfViewer documentId={previewDoc.id} height={600} />}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={!!deleteDocId}
        onOpenChange={(open) => !open && setDeleteDocId(null)}
        title="Delete Document"
        description="Are you sure you want to delete this document? Any active applications using this resume will still retain their reference."
        confirmText="Delete"
        variant="destructive"
        onConfirm={handleDelete}
      />
    </div>
  );
}
