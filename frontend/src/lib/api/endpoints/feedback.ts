import { api } from "../client";
import type {
  ActionItem,
  CompanyFeedback,
  CompanyFeedbackCreateRequest,
  FacultyFeedback,
  FacultyFeedbackCreateRequest,
  FeedbackTrends,
  Page,
  StudentFeedback,
  StudentFeedbackCreateRequest,
  SystemFeedback,
  SystemFeedbackCreateRequest,
  SystemFeedbackSummary,
  UUID,
} from "../types";

export interface StudentFeedbackListParams { company_id?: UUID; internship_id?: UUID; page?: number; page_size?: number }
export interface SystemFeedbackListParams { type?: SystemFeedback["type"]; status?: SystemFeedback["status"]; page?: number; page_size?: number }

export const feedbackApi = {
  // student -> company/internship
  createStudent: (body: StudentFeedbackCreateRequest) => api.post<StudentFeedback>("/feedback/student", body),
  listStudent: (params: StudentFeedbackListParams = {}) => api.get<Page<StudentFeedback>>("/feedback/student", { ...params }),
  studentTrends: (params: { company_id?: UUID; internship_id?: UUID; months?: number } = {}) =>
    api.get<FeedbackTrends>("/feedback/student/trends", { ...params }),
  respondToStudent: (id: UUID, body: string) => api.post<StudentFeedback>(`/feedback/student/${id}/response`, { body }),

  // company/staff -> student
  createCompany: (body: CompanyFeedbackCreateRequest) => api.post<CompanyFeedback>("/feedback/company", body),
  listCompany: (params: { application_id?: UUID; student_id?: UUID; page?: number; page_size?: number } = {}) =>
    api.get<Page<CompanyFeedback>>("/feedback/company", { ...params }),

  // faculty
  createFaculty: (body: FacultyFeedbackCreateRequest) => api.post<FacultyFeedback>("/feedback/faculty", body),
  listFaculty: (params: { internship_id?: UUID; page?: number; page_size?: number } = {}) =>
    api.get<Page<FacultyFeedback>>("/feedback/faculty", { ...params }),

  // system
  createSystem: (body: SystemFeedbackCreateRequest) => api.post<SystemFeedback>("/feedback/system", body),
  listSystem: (params: SystemFeedbackListParams = {}) => api.get<Page<SystemFeedback>>("/feedback/system", { ...params }),
  systemSummary: () => api.get<SystemFeedbackSummary>("/feedback/system/summary"),
  updateSystem: (id: UUID, body: { status?: SystemFeedback["status"]; priority?: SystemFeedback["priority"]; admin_notes?: string }) =>
    api.patch<SystemFeedback>(`/feedback/system/${id}`, body),
  addActionItem: (id: UUID, body: { title: string; assignee_id?: UUID; due_date?: string }) =>
    api.post<ActionItem>(`/feedback/system/${id}/action-items`, body),
  updateActionItem: (id: UUID, body: { status?: ActionItem["status"]; title?: string; due_date?: string | null }) =>
    api.patch<ActionItem>(`/feedback/action-items/${id}`, body),
};
