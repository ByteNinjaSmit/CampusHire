"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { companiesApi, type CompanyListParams } from "../endpoints/companies";
import { qk } from "../keys";
import type { CompanyCreateRequest, UUID } from "../types";

export const useCompanies = (params: CompanyListParams = {}, enabled = true) =>
  useQuery({ queryKey: qk.companies.list(params), queryFn: () => companiesApi.list(params), placeholderData: keepPreviousData, enabled });

export const useCompany = (id: UUID | undefined) =>
  useQuery({ queryKey: qk.companies.detail(id ?? ""), queryFn: () => companiesApi.get(id!), enabled: !!id });

export const useCompanyInternships = (id: UUID | undefined, params: { page?: number; page_size?: number } = {}) =>
  useQuery({ queryKey: qk.companies.internships(id ?? "", params), queryFn: () => companiesApi.internships(id!, params), enabled: !!id });

export const useCompanyRatings = (id: UUID | undefined) =>
  useQuery({ queryKey: qk.companies.ratings(id ?? ""), queryFn: () => companiesApi.ratings(id!), enabled: !!id });

export const useCompanyMembers = (id: UUID | undefined, enabled = true) =>
  useQuery({ queryKey: qk.companies.members(id ?? ""), queryFn: () => companiesApi.members(id!), enabled: !!id && enabled });

function useCompanyMutation<V>(fn: (v: V) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.companies.all });
      qc.invalidateQueries({ queryKey: qk.internships.all });
    },
  });
}

export const useCreateCompany = () => useCompanyMutation((body: CompanyCreateRequest) => companiesApi.create(body));
export const useUpdateCompany = () =>
  useCompanyMutation((v: { id: UUID; body: Partial<CompanyCreateRequest> }) => companiesApi.update(v.id, v.body));
export const useApproveCompany = () => useCompanyMutation((id: UUID) => companiesApi.approve(id));
export const useArchiveCompany = () => useCompanyMutation((id: UUID) => companiesApi.archive(id));
export const useRestoreCompany = () => useCompanyMutation((id: UUID) => companiesApi.restore(id));
export const useDeleteCompany = () => useCompanyMutation((id: UUID) => companiesApi.remove(id));
