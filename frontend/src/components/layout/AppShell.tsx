"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { FullScreenSkeleton } from "@/components/shared/LoadingSkeletons";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { useAuth } from "@/providers/AuthProvider";
import { AppSidebar } from "./AppSidebar";
import { CommandPalette } from "./CommandPalette";
import { PageTransition } from "./PageTransition";
import { Topbar } from "./Topbar";

const COLLAPSE_KEY = "campushire.sidebar.collapsed";

/**
 * Authenticated shell: 264px sidebar (collapsible to 72px, persisted in localStorage), 56px topbar,
 * max-w-7xl content, mobile sidebar as a Sheet. Shows a full-screen skeleton while AuthProvider boots.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    try {
      setCollapsed(localStorage.getItem(COLLAPSE_KEY) === "1");
    } catch {
      /* localStorage unavailable */
    }
  }, []);

  useEffect(() => {
    if (status === "unauthenticated") {
      const next = encodeURIComponent(window.location.pathname + window.location.search);
      router.replace(`/login?next=${next}`);
    }
  }, [status, router]);

  const toggle = () =>
    setCollapsed((c) => {
      const n = !c;
      try {
        localStorage.setItem(COLLAPSE_KEY, n ? "1" : "0");
      } catch {
        /* ignore */
      }
      return n;
    });

  if (status !== "authenticated") return <FullScreenSkeleton />;

  return (
    <div className="min-h-screen bg-background">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-foreground">
        Skip to content
      </a>
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 hidden border-r border-sidebar-border transition-[width] duration-200 md:block",
          collapsed ? "w-[72px]" : "w-[264px]",
        )}
      >
        <AppSidebar collapsed={collapsed} />
      </aside>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-[280px] gap-0 p-0 [&>button]:hidden">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SheetDescription className="sr-only">Main navigation</SheetDescription>
          <AppSidebar onNavigate={() => setMobileOpen(false)} />
        </SheetContent>
      </Sheet>

      <div className={cn("flex min-h-screen flex-col transition-[padding] duration-200", collapsed ? "md:pl-[72px]" : "md:pl-[264px]")}>
        <Topbar collapsed={collapsed} onToggleCollapsed={toggle} onOpenMobileNav={() => setMobileOpen(true)} />
        <main id="main-content" className="flex-1">
          <div className="mx-auto w-full max-w-7xl px-4 py-6 md:px-8 md:py-8">
            <PageTransition>{children}</PageTransition>
          </div>
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
