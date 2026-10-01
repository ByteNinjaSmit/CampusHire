import { api } from "../client";
import type {
  Evaluation,
  EvaluationCreateRequest,
  EvaluationForm,
  EvaluationFormCreateRequest,
  EvaluationSummary,
  Page,
  UUID,
} from "../types";

export interface EvaluationListParams {
  application_id?: UUID;
  internship_id?: UUID;
  student_id?: UUID;
  page?: number;
  page_size?: number;
}

export const evaluationFormsApi = {
  list: (params: { include_archived?: boolean } = {}) => api.get<EvaluationForm[] | Page<EvaluationForm>>("/evaluation-forms", { ...params }),
  create: (body: EvaluationFormCreateRequest) => api.post<EvaluationForm>("/evaluation-forms", body),
  get: (id: UUID) => api.get<EvaluationForm>(`/evaluation-forms/${id}`),
  update: (id: UUID, body: Partial<EvaluationFormCreateRequest>) => api.patch<EvaluationForm>(`/evaluation-forms/${id}`, body),
  archive: (id: UUID) => api.post<EvaluationForm>(`/evaluation-forms/${id}/archive`),
};

export const evaluationsApi = {
  create: (body: EvaluationCreateRequest) => api.post<Evaluation>("/evaluations", body),
  list: (params: EvaluationListParams = {}) => api.get<Page<Evaluation>>("/evaluations", { ...params }),
  get: (id: UUID) => api.get<Evaluation>(`/evaluations/${id}`),
  update: (id: UUID, body: Partial<Omit<EvaluationCreateRequest, "application_id" | "form_id">>) => api.patch<Evaluation>(`/evaluations/${id}`, body),
  archive: (id: UUID) => api.post<Evaluation>(`/evaluations/${id}/archive`),
  remove: (id: UUID) => api.del<void>(`/evaluations/${id}`),
};

export type { EvaluationSummary };
