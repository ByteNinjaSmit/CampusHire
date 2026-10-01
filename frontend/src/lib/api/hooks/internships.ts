"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  internshipsApi,
  type InternshipApplicationsParams,
  type InternshipListParams,
} from "../endpoints/internships";
import { qk } from "../keys";
import type { InternshipCreateRequest, InternshipUpdateRequest, UUID } from "../types";
import type { BulkInternshipsRequest } from "../types-extra";

export const useInternships = (params: InternshipListParams = {}, enabled = true) =>
  useQuery({ queryKey: qk.internships.list(params), queryFn: () => internshipsApi.list(params), placeholderData: keepPreviousData, enabled });

export const useInternshipFacets = () =>
  useQuery({ queryKey: qk.internships.facets(), queryFn: () => internshipsApi.facets(), staleTime: 60_000 });

export const useInternship = (id: UUID | undefined) =>
  useQuery({ queryKey: qk.internships.detail(id ?? ""), queryFn: () => internshipsApi.get(id!), enabled: !!id });

export const useSavedInternships = (params: { page?: number; page_size?: number } = {}, enabled = true) =>
  useQuery({ queryKey: qk.internships.saved(params), queryFn: () => internshipsApi.saved(params), placeholderData: keepPreviousData, enabled });

export const useInternshipApplications = (id: UUID | undefined, params: InternshipApplicationsParams = {}) =>
  useQuery({
    queryKey: qk.internships.applications(id ?? "", params),
    queryFn: () => internshipsApi.applications(id!, params),
    enabled: !!id,
    placeholderData: keepPreviousData,
  });

function useInternshipMutation<V>(fn: (v: V) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.internships.all });
      qc.invalidateQueries({ queryKey: qk.analytics.all });
    },
  });
}

export const useCreateInternship = () => useInternshipMutation((body: InternshipCreateRequest) => internshipsApi.create(body));
export const useUpdateInternship = () =>
  useInternshipMutation((v: { id: UUID; body: InternshipUpdateRequest }) => internshipsApi.update(v.id, v.body));
export const useSubmitInternship = () => useInternshipMutation((id: UUID) => internshipsApi.submit(id));
export const useApproveInternship = () => useInternshipMutation((id: UUID) => internshipsApi.approve(id));
export const useRejectInternship = () =>
  useInternshipMutation((v: { id: UUID; reason: string }) => internshipsApi.reject(v.id, v.reason));
export const useCloseInternship = () => useInternshipMutation((id: UUID) => internshipsApi.close(id));
export const useArchiveInternship = () => useInternshipMutation((id: UUID) => internshipsApi.archive(id));
export const useRestoreInternship = () => useInternshipMutation((id: UUID) => internshipsApi.restore(id));
export const useDeleteInternship = () => useInternshipMutation((id: UUID) => internshipsApi.remove(id));
export const useBulkInternships = () => useInternshipMutation((body: BulkInternshipsRequest) => internshipsApi.bulk(body));

/** Save / unsave with optimistic is_saved flip on cached lists and detail. */
export function useToggleSaveInternship() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: UUID; saved: boolean }) => (v.saved ? internshipsApi.unsave(v.id) : internshipsApi.save(v.id)),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: qk.internships.all });
    },
  });
}
