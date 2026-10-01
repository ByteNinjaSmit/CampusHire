import { api } from "../client";
import type {
  Document,
  DocumentKind,
  DocumentSummary,
  Page,
  UploadTicket,
  UploadUrlRequest,
  UUID,
} from "../types";
import type { DownloadUrl } from "../types-extra";

export interface DocumentListParams {
  kind?: DocumentKind;
  owner_id?: UUID;
  verification_status?: Document["verification_status"];
  page?: number;
  page_size?: number;
}

export const documentsApi = {
  uploadUrl: (body: UploadUrlRequest) => api.post<UploadTicket>("/documents/upload-url", body),
  complete: (id: UUID) => api.post<Document>(`/documents/${id}/complete`),
  list: (params: DocumentListParams = {}) => api.get<Page<Document>>("/documents", { ...params }),
  downloadUrl: (id: UUID) => api.get<DownloadUrl>(`/documents/${id}/download-url`),
  remove: (id: UUID) => api.del<void>(`/documents/${id}`),
  verify: (id: UUID, body: { verification_status: Document["verification_status"]; note?: string }) =>
    api.patch<Document>(`/documents/${id}/verification`, body),
};

export interface UploadProgress { loaded: number; total: number; percent: number }

/**
 * Presigned POST to object storage (MinIO). Uses XHR so we can report progress.
 * Resolves when the storage endpoint answers 2xx (204 expected).
 */
export function postToStorage(
  ticket: UploadTicket,
  file: File,
  onProgress?: (p: UploadProgress) => void,
  signal?: AbortSignal,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const fd = new FormData();
    Object.entries(ticket.upload.fields).forEach(([k, v]) => fd.append(k, v));
    // The file field MUST be last for S3 POST policies.
    fd.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", ticket.upload.url);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress({ loaded: e.loaded, total: e.total, percent: Math.round((e.loaded / e.total) * 100) });
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`Upload failed (${xhr.status}). ${xhr.responseText?.slice(0, 200) ?? ""}`));
    };
    xhr.onerror = () => reject(new Error("Network error while uploading the file."));
    xhr.onabort = () => reject(new DOMException("Upload cancelled", "AbortError"));
    signal?.addEventListener("abort", () => xhr.abort());
    xhr.send(fd);
  });
}

/** Full presigned flow: ticket -> POST to storage -> /complete. */
export async function uploadDocument(
  file: File,
  kind: DocumentKind,
  onProgress?: (p: UploadProgress) => void,
  signal?: AbortSignal,
): Promise<Document> {
  const ticket = await documentsApi.uploadUrl({
    kind,
    filename: file.name,
    content_type: file.type || "application/octet-stream",
    size_bytes: file.size,
  });
  await postToStorage(ticket, file, onProgress, signal);
  return documentsApi.complete(ticket.document_id);
}

export type { DocumentSummary };
