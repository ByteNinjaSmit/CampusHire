"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { evaluationFormsApi, evaluationsApi, type EvaluationListParams } from "../endpoints/evaluations";
import { qk } from "../keys";
import type { EvaluationCreateRequest, EvaluationForm, EvaluationFormCreateRequest, UUID } from "../types";

/** Always resolves to a plain array (the API may return an array or a Page). */
export const useEvaluationForms = (params: { include_archived?: boolean } = {}, enabled = true) =>
  useQuery({
    queryKey: qk.evaluationForms.list(params),
    queryFn: async (): Promise<EvaluationForm[]> => {
      const r = await evaluationFormsApi.list(params);
      return Array.isArray(r) ? r : r.items;
    },
    enabled,
  });

export const useEvaluationForm = (id: UUID | undefined) =>
  useQuery({ queryKey: qk.evaluationForms.detail(id ?? ""), queryFn: () => evaluationFormsApi.get(id!), enabled: !!id });

export function useCreateEvaluationForm() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: EvaluationFormCreateRequest) => evaluationFormsApi.create(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.evaluationForms.all }),
  });
}

export function useUpdateEvaluationForm() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: UUID; body: Partial<EvaluationFormCreateRequest> }) => evaluationFormsApi.update(v.id, v.body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.evaluationForms.all }),
  });
}

export function useArchiveEvaluationForm() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: UUID) => evaluationFormsApi.archive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.evaluationForms.all }),
  });
}

export const useEvaluations = (params: EvaluationListParams = {}, enabled = true) =>
  useQuery({ queryKey: qk.evaluations.list(params), queryFn: () => evaluationsApi.list(params), placeholderData: keepPreviousData, enabled });

export const useEvaluation = (id: UUID | undefined) =>
  useQuery({ queryKey: qk.evaluations.detail(id ?? ""), queryFn: () => evaluationsApi.get(id!), enabled: !!id });

function useEvalMutation<V>(fn: (v: V) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.evaluations.all });
      qc.invalidateQueries({ queryKey: qk.applications.all });
    },
  });
}

export const useCreateEvaluation = () => useEvalMutation((body: EvaluationCreateRequest) => evaluationsApi.create(body));
export const useUpdateEvaluation = () =>
  useEvalMutation((v: { id: UUID; body: Partial<Omit<EvaluationCreateRequest, "application_id" | "form_id">> }) => evaluationsApi.update(v.id, v.body));
export const useArchiveEvaluation = () => useEvalMutation((id: UUID) => evaluationsApi.archive(id));
export const useDeleteEvaluation = () => useEvalMutation((id: UUID) => evaluationsApi.remove(id));
