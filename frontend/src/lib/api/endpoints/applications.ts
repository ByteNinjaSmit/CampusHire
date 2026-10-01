import { api } from "../client";
import type {
  ApplicationCreateRequest,
  ApplicationDetail,
  ApplicationStatusUpdateRequest,
  ApplicationSummary,
  BulkActionResult,
  BulkStatusRequest,
  Page,
  UUID,
} from "../types";
import type { ApplicationListParams, ResumeUrl } from "../types-extra";

export const applicationsApi = {
  create: (body: ApplicationCreateRequest) => api.post<ApplicationDetail>("/applications", body),
  list: (params: ApplicationListParams = {}) => api.get<Page<ApplicationSummary>>("/applications", { ...params }),
  get: (id: UUID) => api.get<ApplicationDetail>(`/applications/${id}`),
  updateStatus: (id: UUID, body: ApplicationStatusUpdateRequest) => api.patch<ApplicationDetail>(`/applications/${id}/status`, body),
  bulkStatus: (body: BulkStatusRequest) => api.post<BulkActionResult>("/applications/bulk-status", body),
  withdraw: (id: UUID, reason?: string) => api.post<ApplicationDetail>(`/applications/${id}/withdraw`, { reason }),
  remove: (id: UUID) => api.del<void>(`/applications/${id}`),
  complete: (id: UUID) => api.post<ApplicationDetail>(`/applications/${id}/complete`),
  resumeUrl: (id: UUID) => api.get<ResumeUrl>(`/applications/${id}/resume-url`),
};
