import { api } from "../client";
import type {
  ApplicationSummary,
  FacultyProfile,
  MessageResponse,
  Page,
  StudentDetail,
  StudentListItem,
  StudentProfile,
  StudentProfileUpdate,
  UUID,
} from "../types";

export interface StudentListParams {
  q?: string;
  department?: string;
  gpa_min?: number;
  gpa_max?: number;
  page?: number;
  page_size?: number;
}

/** GET /students/me: profile plus stats and default resume. */
export type StudentMe = StudentProfile & { stats?: StudentDetail["stats"] };

export const studentsApi = {
  list: (params: StudentListParams = {}) => api.get<Page<StudentListItem>>("/students", { ...params }),
  me: () => api.get<StudentMe>("/students/me"),
  updateMe: (body: StudentProfileUpdate) => api.patch<StudentMe>("/students/me", body),
  setResume: (document_id: UUID) => api.put<StudentMe>("/students/me/resume", { document_id }),
  get: (id: UUID) => api.get<StudentDetail>(`/students/${id}`),
  update: (id: UUID, body: StudentProfileUpdate) => api.patch<StudentDetail>(`/students/${id}`, body),
  deactivate: (id: UUID, reason: string) => api.post<MessageResponse>(`/students/${id}/deactivate`, { reason }),
  applications: (id: UUID, params: { page?: number; page_size?: number } = {}) =>
    api.get<Page<ApplicationSummary>>(`/students/${id}/applications`, { ...params }),
};

export const facultyApi = {
  list: (params: { page?: number; page_size?: number; q?: string } = {}) => api.get<Page<FacultyProfile & { full_name?: string; email?: string }>>("/faculty", { ...params }),
  me: () => api.get<FacultyProfile>("/faculty/me"),
  updateMe: (body: Partial<Pick<FacultyProfile, "department" | "designation" | "employee_id">>) => api.patch<FacultyProfile>("/faculty/me", body),
};
