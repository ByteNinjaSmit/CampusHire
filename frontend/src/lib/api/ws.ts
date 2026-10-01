import { WS_URL, refreshSession } from "./client";
import type { WsMessage } from "./types";
import { getAccessToken } from "@/lib/auth/token-store";

const BACKOFF_MS = [1000, 2000, 5000, 10000];

export type RealtimeStatus = "idle" | "connecting" | "open" | "closed";

export interface RealtimeClient {
  start(): void;
  stop(): void;
}

/**
 * WebSocket client for `GET /api/v1/ws?token=<access_jwt>` (PLAN 6.10).
 * Closes with 4401 -> refresh the token and reconnect; other closes -> backoff 1s, 2s, 5s, 10s (max).
 */
export function createRealtimeClient(opts: {
  onMessage: (msg: WsMessage) => void;
  onStatus?: (s: RealtimeStatus) => void;
}): RealtimeClient {
  let ws: WebSocket | null = null;
  let stopped = true;
  let attempt = 0;
  let timer: ReturnType<typeof setTimeout> | null = null;

  const setStatus = (s: RealtimeStatus) => opts.onStatus?.(s);

  const schedule = (delay: number) => {
    if (stopped) return;
    if (timer) clearTimeout(timer);
    timer = setTimeout(connect, delay);
  };

  async function connect() {
    if (stopped) return;
    let token = getAccessToken();
    if (!token) {
      try {
        token = (await refreshSession()).access_token;
      } catch {
        schedule(BACKOFF_MS[Math.min(attempt++, BACKOFF_MS.length - 1)]);
        return;
      }
    }
    if (stopped) return;
    setStatus("connecting");
    try {
      ws = new WebSocket(`${WS_URL}/api/v1/ws?token=${encodeURIComponent(token)}`);
    } catch {
      schedule(BACKOFF_MS[Math.min(attempt++, BACKOFF_MS.length - 1)]);
      return;
    }
    ws.onopen = () => {
      attempt = 0;
      setStatus("open");
    };
    ws.onmessage = (ev) => {
      let msg: WsMessage;
      try {
        msg = JSON.parse(ev.data as string) as WsMessage;
      } catch {
        return;
      }
      if (msg.type === "ping") {
        ws?.send(JSON.stringify({ type: "pong" }));
        return;
      }
      opts.onMessage(msg);
    };
    ws.onclose = async (ev) => {
      ws = null;
      setStatus("closed");
      if (stopped) return;
      if (ev.code === 4401) {
        try {
          await refreshSession();
          schedule(0);
          return;
        } catch {
          return; // session is gone; AuthProvider will redirect
        }
      }
      schedule(BACKOFF_MS[Math.min(attempt++, BACKOFF_MS.length - 1)]);
    };
    ws.onerror = () => {
      ws?.close();
    };
  }

  return {
    start() {
      if (!stopped) return;
      stopped = false;
      attempt = 0;
      void connect();
    },
    stop() {
      stopped = true;
      if (timer) clearTimeout(timer);
      timer = null;
      const s = ws;
      ws = null;
      if (s) {
        s.onclose = null;
        s.close();
      }
      setStatus("idle");
    },
  };
}
