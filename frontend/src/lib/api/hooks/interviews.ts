"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { interviewsApi, type InterviewListParams } from "../endpoints/interviews";
import { qk } from "../keys";
import type { InterviewCreateRequest, InterviewRescheduleRequest, InterviewResultRequest, UUID } from "../types";

export const useInterviews = (params: InterviewListParams = {}, enabled = true) =>
  useQuery({ queryKey: qk.interviews.list(params), queryFn: () => interviewsApi.list(params), placeholderData: keepPreviousData, enabled });

export const useInterview = (id: UUID | undefined) =>
  useQuery({ queryKey: qk.interviews.detail(id ?? ""), queryFn: () => interviewsApi.get(id!), enabled: !!id });

function useInterviewMutation<V>(fn: (v: V) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.interviews.all });
      qc.invalidateQueries({ queryKey: qk.applications.all });
      qc.invalidateQueries({ queryKey: qk.analytics.all });
    },
  });
}

export const useCreateInterview = () => useInterviewMutation((body: InterviewCreateRequest) => interviewsApi.create(body));
export const useRescheduleInterview = () =>
  useInterviewMutation((v: { id: UUID; body: InterviewRescheduleRequest }) => interviewsApi.reschedule(v.id, v.body));
export const useRecordInterviewResult = () =>
  useInterviewMutation((v: { id: UUID; body: InterviewResultRequest }) => interviewsApi.recordResult(v.id, v.body));
export const useCancelInterview = () =>
  useInterviewMutation((v: { id: UUID; reason: string }) => interviewsApi.cancel(v.id, v.reason));
export const useDeleteInterview = () => useInterviewMutation((id: UUID) => interviewsApi.remove(id));
