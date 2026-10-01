"use client";

import { Bell, CheckCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { EmptyState } from "@/components/shared/EmptyState";
import { ListSkeleton } from "@/components/shared/LoadingSkeletons";
import { useMarkAllNotificationsRead, useMarkNotificationRead, useNotifications, useUnreadCount } from "@/lib/api/hooks/notifications";
import type { Notification } from "@/lib/api/types";
import { formatRelative } from "@/lib/format";
import { cn } from "@/lib/utils";

export function NotificationItem({ n, onOpen }: { n: Notification; onOpen: (n: Notification) => void }) {
  return (
    <button
      type="button"
      onClick={() => onOpen(n)}
      className={cn("flex w-full gap-3 rounded-xl p-3 text-left transition-colors hover:bg-muted/60", !n.read_at && "bg-primary/5")}
    >
      <span className={cn("mt-1.5 size-2 shrink-0 rounded-full", n.read_at ? "bg-transparent" : "bg-primary")} aria-hidden />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium">{n.title}</span>
        <span className="line-clamp-2 text-xs text-muted-foreground">{n.body}</span>
        <span className="mt-1 block text-[11px] text-muted-foreground">{formatRelative(n.created_at)}</span>
      </span>
    </button>
  );
}

export function NotificationBell() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const unread = useUnreadCount().data ?? 0;
  const list = useNotifications({ page_size: 8 }, open);
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();

  const openNotification = (n: Notification) => {
    if (!n.read_at) markRead.mutate(n.id);
    setOpen(false);
    if (n.link) router.push(n.link);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative rounded-xl" aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`} data-testid="notification-bell">
          <Bell className="size-[18px]" />
          {unread > 0 && (
            <span className="absolute right-1 top-1 flex min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold leading-4 text-primary-foreground">
              {unread > 99 ? "99+" : unread}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[360px] max-w-[calc(100vw-1rem)] rounded-2xl p-0">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h3 className="text-sm font-semibold">Notifications</h3>
          <Button variant="ghost" size="xs" className="rounded-lg" disabled={unread === 0 || markAll.isPending} onClick={() => markAll.mutate()}>
            <CheckCheck /> Mark all read
          </Button>
        </div>
        <ScrollArea className="max-h-[360px]">
          <div className="p-1.5">
            {list.isLoading ? (
              <div className="p-3">
                <ListSkeleton rows={4} />
              </div>
            ) : list.data && list.data.items.length > 0 ? (
              list.data.items.map((n) => <NotificationItem key={n.id} n={n} onOpen={openNotification} />)
            ) : (
              <EmptyState title="You are all caught up" description="New updates will show up here." compact className="m-2 border-none bg-transparent" />
            )}
          </div>
        </ScrollArea>
        <div className="border-t p-1.5">
          <Button asChild variant="ghost" size="sm" className="w-full rounded-xl" onClick={() => setOpen(false)}>
            <Link href="/notifications">View all notifications</Link>
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
