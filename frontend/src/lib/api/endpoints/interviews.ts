import { api } from "../client";
import type {
  Interview,
  InterviewCreateRequest,
  InterviewRescheduleRequest,
  InterviewResultRequest,
  InterviewStatus,
  Page,
  UUID,
} from "../types";

export interface InterviewListParams {
  from?: string;
  to?: string;
  status?: InterviewStatus;
  application_id?: UUID;
  page?: number;
  page_size?: number;
}

export const interviewsApi = {
  create: (body: InterviewCreateRequest) => api.post<Interview>("/interviews", body),
  list: (params: InterviewListParams = {}) => api.get<Page<Interview>>("/interviews", { ...params }),
  get: (id: UUID) => api.get<Interview>(`/interviews/${id}`),
  reschedule: (id: UUID, body: InterviewRescheduleRequest) => api.patch<Interview>(`/interviews/${id}/reschedule`, body),
  recordResult: (id: UUID, body: InterviewResultRequest) => api.patch<Interview>(`/interviews/${id}/result`, body),
  cancel: (id: UUID, reason: string) => api.post<Interview>(`/interviews/${id}/cancel`, { reason }),
  remove: (id: UUID) => api.del<void>(`/interviews/${id}`),
};
