"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { feedbackApi, type StudentFeedbackListParams, type SystemFeedbackListParams } from "../endpoints/feedback";
import { qk } from "../keys";
import type {
  ActionItem,
  CompanyFeedbackCreateRequest,
  FacultyFeedbackCreateRequest,
  StudentFeedbackCreateRequest,
  SystemFeedback,
  SystemFeedbackCreateRequest,
  UUID,
} from "../types";

export const useStudentFeedback = (params: StudentFeedbackListParams = {}, enabled = true) =>
  useQuery({ queryKey: qk.feedback.student(params), queryFn: () => feedbackApi.listStudent(params), placeholderData: keepPreviousData, enabled });

export const useStudentFeedbackTrends = (params: { company_id?: UUID; internship_id?: UUID; months?: number } = {}, enabled = true) =>
  useQuery({ queryKey: qk.feedback.studentTrends(params), queryFn: () => feedbackApi.studentTrends(params), enabled });

export const useCompanyFeedback = (params: { application_id?: UUID; student_id?: UUID; page?: number; page_size?: number } = {}, enabled = true) =>
  useQuery({ queryKey: qk.feedback.company(params), queryFn: () => feedbackApi.listCompany(params), placeholderData: keepPreviousData, enabled });

export const useFacultyFeedback = (params: { internship_id?: UUID; page?: number; page_size?: number } = {}, enabled = true) =>
  useQuery({ queryKey: qk.feedback.faculty(params), queryFn: () => feedbackApi.listFaculty(params), placeholderData: keepPreviousData, enabled });

export const useSystemFeedback = (params: SystemFeedbackListParams = {}, enabled = true) =>
  useQuery({ queryKey: qk.feedback.system(params), queryFn: () => feedbackApi.listSystem(params), placeholderData: keepPreviousData, enabled });

export const useSystemFeedbackSummary = (enabled = true) =>
  useQuery({ queryKey: qk.feedback.systemSummary(), queryFn: () => feedbackApi.systemSummary(), enabled });

function useFeedbackMutation<V>(fn: (v: V) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.feedback.all });
      qc.invalidateQueries({ queryKey: qk.applications.all });
      qc.invalidateQueries({ queryKey: qk.companies.all });
    },
  });
}

export const useCreateStudentFeedback = () => useFeedbackMutation((body: StudentFeedbackCreateRequest) => feedbackApi.createStudent(body));
export const useRespondToStudentFeedback = () =>
  useFeedbackMutation((v: { id: UUID; body: string }) => feedbackApi.respondToStudent(v.id, v.body));
export const useCreateCompanyFeedback = () => useFeedbackMutation((body: CompanyFeedbackCreateRequest) => feedbackApi.createCompany(body));
export const useCreateFacultyFeedback = () => useFeedbackMutation((body: FacultyFeedbackCreateRequest) => feedbackApi.createFaculty(body));
export const useCreateSystemFeedback = () => useFeedbackMutation((body: SystemFeedbackCreateRequest) => feedbackApi.createSystem(body));
export const useUpdateSystemFeedback = () =>
  useFeedbackMutation((v: { id: UUID; body: { status?: SystemFeedback["status"]; priority?: SystemFeedback["priority"]; admin_notes?: string } }) =>
    feedbackApi.updateSystem(v.id, v.body));
export const useAddActionItem = () =>
  useFeedbackMutation((v: { id: UUID; body: { title: string; assignee_id?: UUID; due_date?: string } }) => feedbackApi.addActionItem(v.id, v.body));
export const useUpdateActionItem = () =>
  useFeedbackMutation((v: { id: UUID; body: { status?: ActionItem["status"]; title?: string; due_date?: string | null } }) =>
    feedbackApi.updateActionItem(v.id, v.body));
