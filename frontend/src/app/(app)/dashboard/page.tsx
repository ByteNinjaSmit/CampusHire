"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { roleHome } from "@/lib/nav";
import { FullScreenSkeleton } from "@/components/shared/LoadingSkeletons";

export default function DashboardRedirectPage() {
  const { user, status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated" && user) {
      router.replace(roleHome(user.role));
    }
  }, [status, user, router]);

  return <FullScreenSkeleton />;
}
