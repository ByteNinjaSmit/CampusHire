"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "../endpoints/notifications";
import { qk } from "../keys";
import type { UUID } from "../types";

export const useNotifications = (params: { unread_only?: boolean; page?: number; page_size?: number } = {}, enabled = true) =>
  useQuery({ queryKey: qk.notifications.list(params), queryFn: () => notificationsApi.list(params), placeholderData: keepPreviousData, enabled });

export const useUnreadCount = (enabled = true) =>
  useQuery({
    queryKey: qk.notifications.unreadCount(),
    queryFn: () => notificationsApi.unreadCount(),
    enabled,
    select: (d) => d.count,
    refetchInterval: 60_000,
  });

function useNotifMutation<V>(fn: (v: V) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => qc.invalidateQueries({ queryKey: qk.notifications.all }) });
}

export const useMarkNotificationRead = () => useNotifMutation((id: UUID) => notificationsApi.markRead(id));
export const useMarkAllNotificationsRead = () => useNotifMutation(() => notificationsApi.markAllRead());
export const useDeleteNotification = () => useNotifMutation((id: UUID) => notificationsApi.remove(id));
