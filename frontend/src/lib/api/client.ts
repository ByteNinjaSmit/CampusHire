import type { ApiErrorBody, TokenResponse } from "./types";
import {
  clearSession,
  emitSession,
  getAccessToken,
  setAccessToken,
} from "@/lib/auth/token-store";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
export const API_BASE = `${API_URL}/api/v1`;
export const WS_URL = (process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  code: string;
  details: { field: string; message: string }[];
  requestId?: string;

  constructor(status: number, code: string, message: string, details: { field: string; message: string }[] = [], requestId?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }

  /** Field -> message map, handy for RHF setError. */
  get fieldErrors(): Record<string, string> {
    const out: Record<string, string> = {};
    for (const d of this.details) {
      // Pydantic locs can look like "body.email" or "company.name"; keep the tail for flat forms and the full path too.
      const key = d.field.replace(/^body\./, "");
      out[key] = d.message;
      const tail = key.split(".").pop();
      if (tail && !(tail in out)) out[tail] = d.message;
    }
    return out;
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError;
}

export type QueryValue = string | number | boolean | null | undefined | (string | number | boolean)[];
export type QueryParams = Record<string, QueryValue>;

export interface ApiOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  query?: QueryParams;
  signal?: AbortSignal;
  /** Send multipart FormData instead of JSON. */
  formData?: FormData;
  headers?: Record<string, string>;
  /** Skip the access token and the 401 refresh dance (login/register/etc). */
  anonymous?: boolean;
  /** Return the raw Response blob instead of JSON. */
  blob?: boolean;
}

export function buildQuery(query?: QueryParams): string {
  if (!query) return "";
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null || v === "") continue;
    if (Array.isArray(v)) {
      v.forEach((item) => sp.append(k, String(item)));
    } else {
      sp.append(k, String(v));
    }
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

async function parseError(res: Response): Promise<ApiError> {
  let body: Partial<ApiErrorBody> | null = null;
  try {
    body = (await res.json()) as Partial<ApiErrorBody>;
  } catch {
    body = null;
  }
  const err = body?.error;
  return new ApiError(
    res.status,
    err?.code ?? (res.status >= 500 ? "INTERNAL_ERROR" : "BAD_REQUEST"),
    err?.message ?? res.statusText ?? "Request failed",
    err?.details ?? [],
    err?.request_id,
  );
}

// ---------- refresh (single flight) ----------
let refreshPromise: Promise<TokenResponse> | null = null;

/** Rotates the refresh cookie and stores the new access token. Concurrent callers share one request. */
export function refreshSession(): Promise<TokenResponse> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "X-Requested-With": "campushire", Accept: "application/json" },
      });
      if (!res.ok) throw await parseError(res);
      const data = (await res.json()) as TokenResponse;
      setAccessToken(data.access_token);
      emitSession(data.user);
      return data;
    })().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

function redirectToLogin() {
  if (typeof window === "undefined") return;
  const path = window.location.pathname;
  if (path.startsWith("/login") || path === "/" || path.startsWith("/register") || path.startsWith("/forgot-password") || path.startsWith("/reset-password") || path.startsWith("/verify-email")) return;
  const next = encodeURIComponent(path + window.location.search);
  window.location.assign(`/login?next=${next}`);
}

export async function apiFetch<T = unknown>(path: string, opts: ApiOptions = {}): Promise<T> {
  const doFetch = () => {
    const headers: Record<string, string> = { Accept: "application/json", ...opts.headers };
    let body: BodyInit | undefined;
    if (opts.formData) {
      body = opts.formData;
    } else if (opts.body !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(opts.body);
    }
    const token = getAccessToken();
    if (token && !opts.anonymous) headers.Authorization = `Bearer ${token}`;
    return fetch(`${API_BASE}${path}${buildQuery(opts.query)}`, {
      method: opts.method ?? "GET",
      credentials: "include",
      headers,
      body,
      signal: opts.signal,
    });
  };

  let res = await doFetch();

  if (res.status === 401 && !opts.anonymous) {
    const err = await parseError(res.clone());
    const refreshable = err.code === "TOKEN_EXPIRED" || err.code === "UNAUTHENTICATED" || err.code === "TOKEN_INVALID";
    if (refreshable) {
      try {
        await refreshSession();
        res = await doFetch();
      } catch {
        clearSession();
        redirectToLogin();
        throw err;
      }
    }
  }

  if (!res.ok) {
    const err = await parseError(res);
    if (res.status === 401 && !opts.anonymous) {
      clearSession();
      redirectToLogin();
    }
    throw err;
  }

  if (res.status === 204) return undefined as T;
  if (opts.blob) return (await res.blob()) as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

type Q = { query?: QueryParams; signal?: AbortSignal };

export const api = {
  get: <T>(path: string, query?: QueryParams, signal?: AbortSignal) => apiFetch<T>(path, { query, signal }),
  post: <T>(path: string, body?: unknown, o?: Q) => apiFetch<T>(path, { method: "POST", body, ...o }),
  put: <T>(path: string, body?: unknown, o?: Q) => apiFetch<T>(path, { method: "PUT", body, ...o }),
  patch: <T>(path: string, body?: unknown, o?: Q) => apiFetch<T>(path, { method: "PATCH", body, ...o }),
  del: <T = void>(path: string, o?: Q) => apiFetch<T>(path, { method: "DELETE", ...o }),
  upload: <T>(path: string, formData: FormData) => apiFetch<T>(path, { method: "POST", formData }),
  blob: (path: string, query?: QueryParams) => apiFetch<Blob>(path, { query, blob: true }),
};

/** Public endpoint helper (no Authorization header, no refresh). */
export const publicApi = {
  post: <T>(path: string, body?: unknown) => apiFetch<T>(path, { method: "POST", body, anonymous: true }),
};
