"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { authApi } from "@/lib/api/endpoints/auth";
import { refreshSession } from "@/lib/api/client";
import type { LoginRequest, Me, Role, TokenResponse } from "@/lib/api/types";
import { clearSession, onSessionChange, setAccessToken } from "@/lib/auth/token-store";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  user: Me | null;
  role: Role | null;
  status: AuthStatus;
  login: (body: LoginRequest) => Promise<TokenResponse>;
  logout: () => Promise<void>;
  setUser: (user: Me) => void;
  refreshMe: () => Promise<Me | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<Me | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const qc = useQueryClient();
  const router = useRouter();

  // Boot: rotate the refresh cookie to get an access token + Me.
  useEffect(() => {
    let cancelled = false;
    refreshSession()
      .then((data) => {
        if (cancelled) return;
        setUserState(data.user);
        setStatus("authenticated");
      })
      .catch(() => {
        if (cancelled) return;
        clearSession();
        setStatus("unauthenticated");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Keep React state in sync with token-store events (login, refresh, forced sign-out).
  useEffect(
    () =>
      onSessionChange((u) => {
        setUserState(u);
        setStatus(u ? "authenticated" : "unauthenticated");
        if (!u) qc.clear();
      }),
    [qc],
  );

  const login = useCallback(async (body: LoginRequest) => {
    const data = await authApi.login(body);
    setUserState(data.user);
    setStatus("authenticated");
    return data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // best effort; we clear locally regardless
    }
    setAccessToken(null);
    clearSession();
    qc.clear();
    router.replace("/login");
  }, [qc, router]);

  const setUser = useCallback((u: Me) => setUserState(u), []);

  const refreshMe = useCallback(async () => {
    try {
      const me = await authApi.me();
      setUserState(me);
      return me;
    } catch {
      return null;
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, role: user?.role ?? null, status, login, logout, setUser, refreshMe }),
    [user, status, login, logout, setUser, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

/** For code that is only rendered inside the authenticated shell. */
export function useUser(): Me {
  const { user } = useAuth();
  if (!user) throw new Error("useUser called without an authenticated user");
  return user;
}
