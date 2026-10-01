"use client";

import type { ReactNode } from "react";
import type { Role } from "@/lib/api/types";
import { useAuth } from "@/providers/AuthProvider";

/** Renders children only for the listed roles (UI convenience; the API enforces real authorisation). */
export function RoleGate({ roles, children, fallback = null }: { roles: Role[]; children: ReactNode; fallback?: ReactNode }) {
  const { role } = useAuth();
  return <>{role && roles.includes(role) ? children : fallback}</>;
}
