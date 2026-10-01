// Shapes for endpoints that PLAN.md section 4 lists but section 6 does not define (admin, bulk, misc).
// Field names follow the DB columns in section 3. WP8 reconciles these with the backend OpenAPI.
import type {
  ApplicationStatus,
  ISODate,
  ISODateTime,
  Role,
  UUID,
} from "./types";

export type BulkUserAction = "deactivate" | "activate";
export interface BulkUsersRequest { ids: UUID[]; action: BulkUserAction }
export interface BulkInternshipsRequest { ids: UUID[]; action: "approve" | "reject" | "archive" | "close"; reason?: string }
export interface BulkApplicationStatusResult { updated: UUID[]; failed: { id: UUID; code: string; message?: string }[] }

export interface ResumeUrl { url: string; expires_in: number }
export interface DownloadUrl { url: string; expires_in: number }
export interface UnreadCount { count: number }
export interface BulkResult { updated: UUID[]; failed: { id: UUID; code: string; message: string }[] }

export interface CompanyMember { user_id: UUID; full_name: string; email: string; job_title: string | null }

export interface CompanyRatingsResponse {
  summary: import("./types").RatingSummary;
  recent: { id: UUID; overall: number; comments: string | null; student_name: string | null; internship_title: string; created_at: ISODateTime }[];
}

// ---- admin ----
export interface ComponentHealth { status: "ok" | "down" | "degraded"; latency_ms?: number | null; detail?: string | null }
export interface AdminHealth {
  db: ComponentHealth;
  redis: ComponentHealth;
  minio: ComponentHealth & { buckets?: { name: string; size_bytes: number; objects: number }[] };
  celery: ComponentHealth & { workers?: number };
  queue_depth?: number;
  disk_usage_bytes?: number;
  checked_at?: ISODateTime;
}
export interface MetricPoint { minute: ISODateTime; count: number; errors: number; p50_ms: number | null; p95_ms: number | null }
export interface AdminMetrics { minutes: number; points: MetricPoint[] }
export interface AuditLog {
  id: number;
  actor_id: UUID | null;
  actor_name?: string | null;
  action: string;
  entity_type: string;
  entity_id: UUID | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  ip: string | null;
  created_at: ISODateTime;
}
export interface CompliancePolicy { id: UUID; code: string; name: string; description: string | null; is_active: boolean; severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | string }
export interface CompliancePolicyCreate { code: string; name: string; description?: string; is_active?: boolean; severity?: string }
export interface CompliancePolicyUpdate { name?: string; description?: string; is_active?: boolean; severity?: string }
export type ViolationStatus = "OPEN" | "RESOLVED" | "DISMISSED";
export interface PolicyViolation {
  id: UUID;
  policy_id: UUID;
  policy_code: string;
  policy_name?: string;
  entity_type: string;
  entity_id: UUID;
  details: Record<string, unknown>;
  status: ViolationStatus;
  resolved_by?: UUID | null;
  resolved_at?: ISODateTime | null;
  note: string | null;
  created_at: ISODateTime;
}
export type ExportEntity = "students" | "companies" | "internships" | "applications" | "feedback";
export interface AdminExportRequest { entity: ExportEntity; format: "csv" | "xlsx"; filters?: Record<string, unknown> }
export type ImportEntity = ExportEntity;
export interface ReportExportRequest { format: "pdf" | "xlsx"; params?: Record<string, unknown> }
export interface ReportParams { from?: ISODate; to?: ISODate; internship_id?: UUID; company_id?: UUID; student_id?: UUID }

export interface UserListParams { role?: Role; q?: string; is_active?: boolean; page?: number; page_size?: number }
export interface ApplicationListParams { status?: ApplicationStatus; internship_id?: UUID; q?: string; page?: number; page_size?: number }
