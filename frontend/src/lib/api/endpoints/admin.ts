import { api } from "../client";
import type { Job, Page, UUID } from "../types";
import type {
  AdminExportRequest,
  AdminHealth,
  AdminMetrics,
  AuditLog,
  CompliancePolicy,
  CompliancePolicyCreate,
  CompliancePolicyUpdate,
  ImportEntity,
  PolicyViolation,
  ViolationStatus,
} from "../types-extra";

export interface AuditLogParams {
  actor_id?: UUID;
  entity_type?: string;
  action?: string;
  from?: string;
  to?: string;
  page?: number;
  page_size?: number;
}

export const adminApi = {
  health: () => api.get<AdminHealth>("/admin/health"),
  metrics: (minutes = 60) => api.get<AdminMetrics>("/admin/metrics", { minutes }),
  auditLogs: (params: AuditLogParams = {}) => api.get<Page<AuditLog>>("/admin/audit-logs", { ...params }),

  policies: () => api.get<CompliancePolicy[] | Page<CompliancePolicy>>("/admin/compliance/policies"),
  createPolicy: (body: CompliancePolicyCreate) => api.post<CompliancePolicy>("/admin/compliance/policies", body),
  updatePolicy: (id: UUID, body: CompliancePolicyUpdate) => api.patch<CompliancePolicy>(`/admin/compliance/policies/${id}`, body),
  violations: (params: { status?: ViolationStatus; policy_code?: string; page?: number; page_size?: number } = {}) =>
    api.get<Page<PolicyViolation>>("/admin/compliance/violations", { ...params }),
  updateViolation: (id: UUID, body: { status: ViolationStatus; note?: string }) =>
    api.patch<PolicyViolation>(`/admin/compliance/violations/${id}`, body),
  runScan: () => api.post<Job>("/admin/compliance/scan"),

  export: (body: AdminExportRequest) => api.post<Job>("/admin/export", body),
  import: (entity: ImportEntity, file: File) => {
    const fd = new FormData();
    fd.append("entity", entity);
    fd.append("file", file);
    return api.upload<Job>("/admin/import", fd);
  },
  importTemplate: (entity: ImportEntity) => api.blob(`/admin/import/template/${entity}`),
};
