"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usersApi } from "../endpoints/users";
import { qk } from "../keys";
import type { AdminCreateUserRequest, UpdateUserRequest, UUID } from "../types";
import type { BulkUsersRequest, UserListParams } from "../types-extra";
import { useAuth } from "@/providers/AuthProvider";

export const useUsers = (params: UserListParams = {}, enabled = true) =>
  useQuery({ queryKey: qk.users.list(params), queryFn: () => usersApi.list(params), placeholderData: keepPreviousData, enabled });

export const useUser = (id: UUID | undefined) =>
  useQuery({ queryKey: qk.users.detail(id ?? ""), queryFn: () => usersApi.get(id!), enabled: !!id });

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AdminCreateUserRequest) => usersApi.create(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.users.all }),
  });
}

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: UUID; body: UpdateUserRequest }) => usersApi.update(v.id, v.body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.users.all }),
  });
}

export function useDeactivateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: UUID; reason: string }) => usersApi.deactivate(v.id, v.reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.users.all });
      qc.invalidateQueries({ queryKey: qk.students.all });
    },
  });
}

export function useActivateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: UUID) => usersApi.activate(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.users.all });
      qc.invalidateQueries({ queryKey: qk.students.all });
    },
  });
}

export function useBulkUsers() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: BulkUsersRequest) => usersApi.bulk(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.users.all }),
  });
}

/** PATCH /users/me, and refreshes the session user held by AuthProvider. */
export function useUpdateMe() {
  const { setUser } = useAuth();
  return useMutation({
    mutationFn: (body: { full_name?: string; phone?: string | null; avatar_url?: string | null }) => usersApi.updateMe(body),
    onSuccess: (me) => {
      if (me && typeof me === "object" && "id" in me) setUser(me);
    },
  });
}
