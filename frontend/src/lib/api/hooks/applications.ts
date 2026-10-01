"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { applicationsApi } from "../endpoints/applications";
import { qk } from "../keys";
import type { ApplicationCreateRequest, ApplicationStatusUpdateRequest, BulkStatusRequest, UUID } from "../types";
import type { ApplicationListParams } from "../types-extra";

export const useApplications = (params: ApplicationListParams = {}, enabled = true) =>
  useQuery({ queryKey: qk.applications.list(params), queryFn: () => applicationsApi.list(params), placeholderData: keepPreviousData, enabled });

export const useApplication = (id: UUID | undefined) =>
  useQuery({ queryKey: qk.applications.detail(id ?? ""), queryFn: () => applicationsApi.get(id!), enabled: !!id });

export const useResumeUrl = (id: UUID | undefined) =>
  useQuery({ queryKey: qk.applications.resumeUrl(id ?? ""), queryFn: () => applicationsApi.resumeUrl(id!), enabled: !!id, staleTime: 4 * 60_000 });

function useAppMutation<V>(fn: (v: V) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.applications.all });
      qc.invalidateQueries({ queryKey: qk.internships.all });
      qc.invalidateQueries({ queryKey: qk.interviews.all });
      qc.invalidateQueries({ queryKey: qk.analytics.all });
      qc.invalidateQueries({ queryKey: qk.students.all });
    },
  });
}

export const useCreateApplication = () => useAppMutation((body: ApplicationCreateRequest) => applicationsApi.create(body));
export const useUpdateApplicationStatus = () =>
  useAppMutation((v: { id: UUID; body: ApplicationStatusUpdateRequest }) => applicationsApi.updateStatus(v.id, v.body));
export const useBulkApplicationStatus = () => useAppMutation((body: BulkStatusRequest) => applicationsApi.bulkStatus(body));
export const useWithdrawApplication = () =>
  useAppMutation((v: { id: UUID; reason?: string }) => applicationsApi.withdraw(v.id, v.reason));
export const useDeleteApplication = () => useAppMutation((id: UUID) => applicationsApi.remove(id));
export const useCompleteApplication = () => useAppMutation((id: UUID) => applicationsApi.complete(id));
