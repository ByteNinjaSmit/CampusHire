import { api } from "../client";
import type { Notification, Page, UUID } from "../types";
import type { UnreadCount } from "../types-extra";

export const notificationsApi = {
  list: (params: { unread_only?: boolean; page?: number; page_size?: number } = {}) =>
    api.get<Page<Notification>>("/notifications", { ...params }),
  unreadCount: () => api.get<UnreadCount>("/notifications/unread-count"),
  markRead: (id: UUID) => api.post<Notification | void>(`/notifications/${id}/read`),
  markAllRead: () => api.post<void>("/notifications/read-all"),
  remove: (id: UUID) => api.del<void>(`/notifications/${id}`),
};
