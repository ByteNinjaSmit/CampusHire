import { api } from "../client";
import type {
  AdminCreateUserRequest,
  Me,
  MessageResponse,
  Page,
  UpdateUserRequest,
  UserSummary,
  UUID,
} from "../types";
import type { BulkResult, BulkUsersRequest, UserListParams } from "../types-extra";

export const usersApi = {
  list: (params: UserListParams = {}) => api.get<Page<UserSummary>>("/users", { ...params }),
  create: (body: AdminCreateUserRequest) => api.post<UserSummary>("/users", body),
  get: (id: UUID) => api.get<UserSummary>(`/users/${id}`),
  update: (id: UUID, body: UpdateUserRequest) => api.patch<UserSummary>(`/users/${id}`, body),
  deactivate: (id: UUID, reason: string) => api.post<MessageResponse>(`/users/${id}/deactivate`, { reason }),
  activate: (id: UUID) => api.post<MessageResponse>(`/users/${id}/activate`),
  bulk: (body: BulkUsersRequest) => api.post<BulkResult>("/users/bulk", body),
  updateMe: (body: { full_name?: string; phone?: string | null; avatar_url?: string | null }) => api.patch<Me>("/users/me", body),
};
