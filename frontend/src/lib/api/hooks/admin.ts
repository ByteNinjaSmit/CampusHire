"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi, type AuditLogParams } from "../endpoints/admin";
import { qk } from "../keys";
import type { UUID } from "../types";
import type {
  AdminExportRequest,
  CompliancePolicy,
  CompliancePolicyCreate,
  CompliancePolicyUpdate,
  ImportEntity,
  ViolationStatus,
} from "../types-extra";

export const useAdminHealth = (enabled = true) =>
  useQuery({ queryKey: qk.admin.health(), queryFn: () => adminApi.health(), enabled, refetchInterval: 15_000 });

export const useAdminMetrics = (minutes = 60, enabled = true) =>
  useQuery({ queryKey: qk.admin.metrics(minutes), queryFn: () => adminApi.metrics(minutes), enabled, refetchInterval: 30_000 });

export const useAuditLogs = (params: AuditLogParams = {}, enabled = true) =>
  useQuery({ queryKey: qk.admin.auditLogs(params), queryFn: () => adminApi.auditLogs(params), placeholderData: keepPreviousData, enabled });

export const useCompliancePolicies = (enabled = true) =>
  useQuery({
    queryKey: qk.admin.policies(),
    queryFn: async (): Promise<CompliancePolicy[]> => {
      const r = await adminApi.policies();
      return Array.isArray(r) ? r : r.items;
    },
    enabled,
  });

export const useViolations = (params: { status?: ViolationStatus; policy_code?: string; page?: number; page_size?: number } = {}, enabled = true) =>
  useQuery({ queryKey: qk.admin.violations(params), queryFn: () => adminApi.violations(params), placeholderData: keepPreviousData, enabled });

function useAdminMutation<V>(fn: (v: V) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.admin.all });
      qc.invalidateQueries({ queryKey: qk.jobs.all });
    },
  });
}

export const useCreatePolicy = () => useAdminMutation((body: CompliancePolicyCreate) => adminApi.createPolicy(body));
export const useUpdatePolicy = () => useAdminMutation((v: { id: UUID; body: CompliancePolicyUpdate }) => adminApi.updatePolicy(v.id, v.body));
export const useUpdateViolation = () =>
  useAdminMutation((v: { id: UUID; status: ViolationStatus; note?: string }) => adminApi.updateViolation(v.id, { status: v.status, note: v.note }));
export const useRunComplianceScan = () => useAdminMutation(() => adminApi.runScan());
export const useAdminExport = () => useAdminMutation((body: AdminExportRequest) => adminApi.export(body));
export const useAdminImport = () => useAdminMutation((v: { entity: ImportEntity; file: File }) => adminApi.import(v.entity, v.file));
