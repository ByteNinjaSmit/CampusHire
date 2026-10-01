"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { documentsApi, uploadDocument, type DocumentListParams, type UploadProgress } from "../endpoints/documents";
import { qk } from "../keys";
import type { Document, DocumentKind, UUID } from "../types";

export const useDocuments = (params: DocumentListParams = {}, enabled = true) =>
  useQuery({ queryKey: qk.documents.list(params), queryFn: () => documentsApi.list(params), placeholderData: keepPreviousData, enabled });

export const useDocumentDownloadUrl = (id: UUID | undefined) =>
  useQuery({ queryKey: qk.documents.downloadUrl(id ?? ""), queryFn: () => documentsApi.downloadUrl(id!), enabled: !!id, staleTime: 4 * 60_000 });

/** Full presigned-POST flow (ticket -> storage -> /complete). */
export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { file: File; kind: DocumentKind; onProgress?: (p: UploadProgress) => void; signal?: AbortSignal }) =>
      uploadDocument(v.file, v.kind, v.onProgress, v.signal),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.documents.all }),
  });
}

export function useDeleteDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: UUID) => documentsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.documents.all });
      qc.invalidateQueries({ queryKey: qk.students.all });
    },
  });
}

export function useVerifyDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: UUID; verification_status: Document["verification_status"]; note?: string }) =>
      documentsApi.verify(v.id, { verification_status: v.verification_status, note: v.note }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.documents.all });
      qc.invalidateQueries({ queryKey: qk.admin.all });
    },
  });
}
