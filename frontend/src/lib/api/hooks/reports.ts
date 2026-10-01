"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { analyticsApi, jobsApi, reportsApi } from "../endpoints/reports";
import { qk } from "../keys";
import type { Job, UUID } from "../types";
import type { ReportExportRequest, ReportParams } from "../types-extra";

export const useReports = (enabled = true) =>
  useQuery({ queryKey: qk.reports.list(), queryFn: () => reportsApi.list(), enabled, staleTime: 5 * 60_000 });

export const useReport = (key: string | undefined, params: ReportParams = {}, enabled = true) =>
  useQuery({ queryKey: qk.reports.detail(key ?? "", params), queryFn: () => reportsApi.get(key!, params), enabled: !!key && enabled });

export const useExportReport = () =>
  useMutation({ mutationFn: (v: { key: string; body: ReportExportRequest }) => reportsApi.export(v.key, v.body) });

const isActive = (j: Job | undefined) => !j || j.status === "QUEUED" || j.status === "RUNNING";

/** Polls GET /jobs/{id} every 2 s until the job finishes. The realtime socket also writes into this cache. */
export const useJob = (id: UUID | undefined) =>
  useQuery({
    queryKey: qk.jobs.detail(id ?? ""),
    queryFn: () => jobsApi.get(id!),
    enabled: !!id,
    refetchInterval: (q) => (isActive(q.state.data) ? 2000 : false),
  });

export const useJobs = (params: { type?: Job["type"]; page?: number; page_size?: number } = {}, enabled = true) =>
  useQuery({ queryKey: qk.jobs.list(params), queryFn: () => jobsApi.list(params), placeholderData: keepPreviousData, enabled });

export const useDashboard = (enabled = true) =>
  useQuery({ queryKey: qk.analytics.dashboard(), queryFn: () => analyticsApi.dashboard(), enabled });

export function useInvalidateJobs() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: qk.jobs.all });
}
