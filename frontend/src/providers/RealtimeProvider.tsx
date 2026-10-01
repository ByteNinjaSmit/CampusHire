"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { qk } from "@/lib/api/keys";
import type { Job, WsMessage } from "@/lib/api/types";
import { createRealtimeClient, type RealtimeStatus } from "@/lib/api/ws";
import { useAuth } from "./AuthProvider";

const RealtimeContext = createContext<{ status: RealtimeStatus }>({ status: "idle" });

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const { status: authStatus, user } = useAuth();
  const qc = useQueryClient();
  const router = useRouter();
  const [status, setStatus] = useState<RealtimeStatus>("idle");
  const routerRef = useRef(router);
  useEffect(() => {
    routerRef.current = router;
  }, [router]);

  const userId = user?.id;
  useEffect(() => {
    if (authStatus !== "authenticated" || !userId) return;

    const handle = (msg: WsMessage) => {
      switch (msg.type) {
        case "notification": {
          qc.invalidateQueries({ queryKey: qk.notifications.all });
          const n = msg.data;
          toast(n.title, {
            description: n.body,
            action: n.link ? { label: "View", onClick: () => routerRef.current.push(n.link as string) } : undefined,
          });
          break;
        }
        case "unread_count":
          qc.setQueryData(qk.notifications.unreadCount(), { count: msg.data.count });
          break;
        case "job": {
          const job: Job = msg.data;
          qc.setQueryData(qk.jobs.detail(job.id), job);
          qc.invalidateQueries({ queryKey: qk.jobs.list() });
          break;
        }
        default:
          break;
      }
    };

    const client = createRealtimeClient({ onMessage: handle, onStatus: setStatus });
    client.start();
    return () => client.stop();
  }, [authStatus, userId, qc]);

  return <RealtimeContext.Provider value={{ status }}>{children}</RealtimeContext.Provider>;
}

export const useRealtimeStatus = () => useContext(RealtimeContext).status;
