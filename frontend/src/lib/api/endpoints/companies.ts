import { api } from "../client";
import type {
  Company,
  CompanyCreateRequest,
  CompanyStatus,
  CompanySummary,
  InternshipSummary,
  MessageResponse,
  Page,
  UUID,
} from "../types";
import type { CompanyMember, CompanyRatingsResponse } from "../types-extra";

export interface CompanyListParams {
  q?: string;
  location?: string;
  industry?: string;
  status?: CompanyStatus;
  page?: number;
  page_size?: number;
}

export const companiesApi = {
  list: (params: CompanyListParams = {}) => api.get<Page<CompanySummary>>("/companies", { ...params }),
  create: (body: CompanyCreateRequest) => api.post<Company>("/companies", body),
  get: (id: UUID) => api.get<Company>(`/companies/${id}`),
  update: (id: UUID, body: Partial<CompanyCreateRequest>) => api.patch<Company>(`/companies/${id}`, body),
  approve: (id: UUID) => api.post<Company>(`/companies/${id}/approve`),
  archive: (id: UUID) => api.post<Company>(`/companies/${id}/archive`),
  restore: (id: UUID) => api.post<Company>(`/companies/${id}/restore`),
  remove: (id: UUID) => api.del<MessageResponse | void>(`/companies/${id}`),
  internships: (id: UUID, params: { page?: number; page_size?: number } = {}) =>
    api.get<Page<InternshipSummary>>(`/companies/${id}/internships`, { ...params }),
  ratings: (id: UUID) => api.get<CompanyRatingsResponse>(`/companies/${id}/ratings`),
  members: (id: UUID) => api.get<CompanyMember[]>(`/companies/${id}/members`),
};
