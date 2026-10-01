import { api } from "../client";
import type { DashboardData, Job, Page, ReportData, ReportMeta, UUID } from "../types";
import type { ReportExportRequest, ReportParams } from "../types-extra";

export const reportsApi = {
  list: () => api.get<ReportMeta[]>("/reports"),
  get: (key: string, params: ReportParams = {}) => api.get<ReportData>(`/reports/${key}`, { ...params }),
  export: (key: string, body: ReportExportRequest) => api.post<Job>(`/reports/${key}/export`, body),
};

export const jobsApi = {
  get: (id: UUID) => api.get<Job>(`/jobs/${id}`),
  list: (params: { type?: Job["type"]; page?: number; page_size?: number } = {}) => api.get<Page<Job>>("/jobs", { ...params }),
};

export const analyticsApi = {
  dashboard: () => api.get<DashboardData>("/analytics/dashboard"),
};
