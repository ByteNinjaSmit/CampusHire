"use client";

import { useState } from "react";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import {
  Bell,
  Check,
  CheckCheck,
  Trash2,
  ExternalLink,
  Info,
  Calendar,
  Briefcase,
  AlertCircle,
  FileCheck,
} from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useNotifications,
  useMarkNotificationRead,
  useMarkAllNotificationsRead,
  useDeleteNotification,
} from "@/lib/api/hooks/notifications";
import type { Notification } from "@/lib/api/types";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";

function getNotificationIcon(type: string) {
  if (type.includes("INTERVIEW")) return <Calendar className="size-5 text-amber-500" />;
  if (type.includes("APPLICATION")) return <Briefcase className="size-5 text-indigo-500" />;
  if (type.includes("EVALUATION") || type.includes("VERIF")) return <FileCheck className="size-5 text-emerald-500" />;
  if (type.includes("ALERT") || type.includes("REJECT") || type.includes("CANCEL")) return <AlertCircle className="size-5 text-rose-500" />;
  return <Info className="size-5 text-sky-500" />;
}

export default function NotificationsPage() {
  const [tab, setTab] = useState<"all" | "unread">("all");
  const { data, isLoading } = useNotifications({
    unread_only: tab === "unread",
    page: 1,
    page_size: 50,
  });

  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();
  const removeNotif = useDeleteNotification();

  const notifications = data?.items ?? [];
  const unreadCount = notifications.filter((n) => !n.read_at).length;

  const handleMarkRead = (id: string) => {
    markRead.mutate(id, {
      onError: (err) => toast.error(errorMessage(err, "Failed to mark as read")),
    });
  };

  const handleMarkAllRead = () => {
    markAllRead.mutate(undefined, {
      onSuccess: () => toast.success("All notifications marked as read"),
      onError: (err) => toast.error(errorMessage(err, "Failed to mark all as read")),
    });
  };

  const handleDelete = (id: string) => {
    removeNotif.mutate(id, {
      onSuccess: () => toast.success("Notification removed"),
      onError: (err) => toast.error(errorMessage(err, "Failed to delete notification")),
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notifications"
        description="Stay informed about your application status, interview schedules, and platform alerts."
        actions={
          unreadCount > 0 ? (
            <Button
              variant="outline"
              size="sm"
              onClick={handleMarkAllRead}
              disabled={markAllRead.isPending}
              className="gap-1.5"
            >
              <CheckCheck className="size-4" />
              Mark all as read
            </Button>
          ) : undefined
        }
      />

      <div className="flex items-center justify-between border-b pb-4">
        <Tabs value={tab} onValueChange={(v) => setTab(v as "all" | "unread")}>
          <TabsList className="bg-muted/60">
            <TabsTrigger value="all" className="gap-2">
              All
              <Badge variant="secondary" className="px-1.5 py-0.5 text-xs">
                {data?.total ?? 0}
              </Badge>
            </TabsTrigger>
            <TabsTrigger value="unread" className="gap-2">
              Unread
              {unreadCount > 0 && (
                <Badge variant="default" className="px-1.5 py-0.5 text-xs">
                  {unreadCount}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {isLoading ? (
        <LoadingCardGrid count={4} />
      ) : notifications.length === 0 ? (
        <EmptyState
          icon={Bell}
          title={tab === "unread" ? "No unread notifications" : "No notifications yet"}
          description={
            tab === "unread"
              ? "You are completely caught up! We will notify you when there are new updates."
              : "Updates about your applications, interviews, and deadlines will appear here."
          }
        />
      ) : (
        <div className="divide-y divide-border/60 rounded-2xl border bg-card/60 shadow-sm backdrop-blur-sm">
          {notifications.map((n: Notification) => (
            <div
              key={n.id}
              className={`flex items-start gap-4 p-4 transition-colors hover:bg-muted/40 ${
                !n.read_at ? "bg-primary/5" : ""
              }`}
            >
              <div className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-xl bg-background shadow-xs ring-1 ring-border">
                {getNotificationIcon(n.type)}
              </div>

              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <h4 className={`text-sm font-medium ${!n.read_at ? "text-foreground font-semibold" : "text-muted-foreground"}`}>
                    {n.title}
                  </h4>
                  {!n.read_at && (
                    <span className="size-2 rounded-full bg-primary" title="Unread" />
                  )}
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">{n.body}</p>
                <div className="flex items-center gap-4 pt-1 text-xs text-muted-foreground">
                  <span>
                    {n.created_at
                      ? formatDistanceToNow(new Date(n.created_at), { addSuffix: true })
                      : "Recently"}
                  </span>
                  {n.link && (
                    <Link
                      href={n.link}
                      className="inline-flex items-center gap-1 font-medium text-primary hover:underline"
                    >
                      View details <ExternalLink className="size-3" />
                    </Link>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-1">
                {!n.read_at && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-8 text-muted-foreground hover:text-foreground"
                    onClick={() => handleMarkRead(n.id)}
                    title="Mark as read"
                  >
                    <Check className="size-4" />
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8 text-muted-foreground hover:text-destructive"
                  onClick={() => handleDelete(n.id)}
                  title="Delete"
                >
                  <Trash2 className="size-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
