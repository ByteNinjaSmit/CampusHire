// In-memory access token (never persisted). The refresh token lives in an HttpOnly cookie managed by the API.
import type { Me } from "@/lib/api/types";

let accessToken: string | null = null;

type TokenListener = (token: string | null) => void;
type SessionListener = (user: Me | null) => void;

const tokenListeners = new Set<TokenListener>();
const sessionListeners = new Set<SessionListener>();

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null) {
  accessToken = token;
  tokenListeners.forEach((l) => l(token));
}

/** Subscribe to token changes (used by the realtime socket to reconnect with a fresh JWT). */
export function onTokenChange(listener: TokenListener): () => void {
  tokenListeners.add(listener);
  return () => tokenListeners.delete(listener);
}

/**
 * Subscribe to session changes: called with the Me object after login/refresh,
 * and with null when the session was cleared (refresh failed / logout).
 */
export function onSessionChange(listener: SessionListener): () => void {
  sessionListeners.add(listener);
  return () => sessionListeners.delete(listener);
}

export function emitSession(user: Me | null) {
  sessionListeners.forEach((l) => l(user));
}

/** ch_role is a non-HttpOnly routing hint (Path=/). Remove it so proxy.ts stops treating us as logged in. */
export function clearRoleCookie() {
  if (typeof document === "undefined") return;
  document.cookie = "ch_role=; Max-Age=0; Path=/; SameSite=Lax";
}

export function clearSession() {
  setAccessToken(null);
  clearRoleCookie();
  emitSession(null);
}
