"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { facultyApi, studentsApi, type StudentListParams } from "../endpoints/students";
import { qk } from "../keys";
import type { FacultyProfile, StudentProfileUpdate, UUID } from "../types";

export const useStudents = (params: StudentListParams = {}, enabled = true) =>
  useQuery({ queryKey: qk.students.list(params), queryFn: () => studentsApi.list(params), placeholderData: keepPreviousData, enabled });

export const useMyStudentProfile = (enabled = true) =>
  useQuery({ queryKey: qk.students.me(), queryFn: () => studentsApi.me(), enabled });

export const useStudent = (id: UUID | undefined) =>
  useQuery({ queryKey: qk.students.detail(id ?? ""), queryFn: () => studentsApi.get(id!), enabled: !!id });

export const useStudentApplications = (id: UUID | undefined, params: { page?: number; page_size?: number } = {}) =>
  useQuery({ queryKey: qk.students.applications(id ?? "", params), queryFn: () => studentsApi.applications(id!, params), enabled: !!id });

export function useUpdateMyStudentProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: StudentProfileUpdate) => studentsApi.updateMe(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.students.all });
      qc.invalidateQueries({ queryKey: qk.auth.all });
    },
  });
}

export function useSetDefaultResume() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (document_id: UUID) => studentsApi.setResume(document_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.students.all });
      qc.invalidateQueries({ queryKey: qk.documents.all });
    },
  });
}

export function useUpdateStudent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: UUID; body: StudentProfileUpdate }) => studentsApi.update(v.id, v.body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.students.all }),
  });
}

export function useDeactivateStudent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: UUID; reason: string }) => studentsApi.deactivate(v.id, v.reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.students.all });
      qc.invalidateQueries({ queryKey: qk.users.all });
    },
  });
}

export const useMyFacultyProfile = (enabled = true) =>
  useQuery({ queryKey: qk.faculty.me(), queryFn: () => facultyApi.me(), enabled });

export const useFacultyList = (params: { page?: number; page_size?: number; q?: string } = {}, enabled = true) =>
  useQuery({ queryKey: qk.faculty.list(params), queryFn: () => facultyApi.list(params), enabled });

export function useUpdateMyFacultyProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Pick<FacultyProfile, "department" | "designation" | "employee_id">>) => facultyApi.updateMe(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.faculty.all });
      qc.invalidateQueries({ queryKey: qk.auth.all });
    },
  });
}
