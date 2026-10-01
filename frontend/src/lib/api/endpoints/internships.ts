import { api } from "../client";
import type {
  ApplicationSummary,
  ApplicationStatus,
  BulkActionResult,
  Internship,
  InternshipCreateRequest,
  InternshipFacets,
  InternshipStatus,
  InternshipSummary,
  InternshipUpdateRequest,
  Page,
  UUID,
  WorkMode,
} from "../types";
import type { BulkInternshipsRequest } from "../types-extra";

export type InternshipSort = "relevance" | "newest" | "stipend_desc" | "deadline_asc";

export interface InternshipListParams {
  q?: string;
  domain?: string[];
  company_id?: UUID[];
  location?: string;
  work_mode?: WorkMode;
  stipend_min?: number;
  stipend_max?: number;
  duration_min?: number;
  duration_max?: number;
  status?: InternshipStatus;
  mine?: boolean;
  include_archived?: boolean;
  sort?: InternshipSort;
  page?: number;
  page_size?: number;
}

export interface InternshipApplicationsParams {
  status?: ApplicationStatus;
  q?: string;
  page?: number;
  page_size?: number;
}

export const internshipsApi = {
  list: (params: InternshipListParams = {}) => api.get<Page<InternshipSummary>>("/internships", { ...params }),
  facets: () => api.get<InternshipFacets>("/internships/facets"),
  create: (body: InternshipCreateRequest) => api.post<Internship>("/internships", body),
  get: (id: UUID) => api.get<Internship>(`/internships/${id}`),
  update: (id: UUID, body: InternshipUpdateRequest) => api.patch<Internship>(`/internships/${id}`, body),
  submit: (id: UUID) => api.post<Internship>(`/internships/${id}/submit`),
  approve: (id: UUID) => api.post<Internship>(`/internships/${id}/approve`),
  reject: (id: UUID, reason: string) => api.post<Internship>(`/internships/${id}/reject`, { reason }),
  close: (id: UUID) => api.post<Internship>(`/internships/${id}/close`),
  archive: (id: UUID) => api.post<Internship>(`/internships/${id}/archive`),
  restore: (id: UUID) => api.post<Internship>(`/internships/${id}/restore`),
  remove: (id: UUID) => api.del<void>(`/internships/${id}`),
  bulk: (body: BulkInternshipsRequest) => api.post<BulkActionResult>("/internships/bulk", body),
  save: (id: UUID) => api.post<void>(`/internships/${id}/save`),
  unsave: (id: UUID) => api.del<void>(`/internships/${id}/save`),
  saved: (params: { page?: number; page_size?: number } = {}) => api.get<Page<InternshipSummary>>("/internships/saved", { ...params }),
  applications: (id: UUID, params: InternshipApplicationsParams = {}) =>
    api.get<Page<ApplicationSummary>>(`/internships/${id}/applications`, { ...params }),
};
