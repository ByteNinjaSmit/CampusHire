"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "@/components/shared/Logo";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { roleHome, navFor, type NavItem } from "@/lib/nav";
import { ROLE_LABELS } from "@/lib/status";
import { cn } from "@/lib/utils";
import { useAuth } from "@/providers/AuthProvider";

function isActive(item: NavItem, pathname: string, siblings: NavItem[]): boolean {
  if (pathname === item.href) return true;
  if (item.exact) return false;
  if (!pathname.startsWith(item.href + "/")) return false;
  // Do not highlight a parent when a longer sibling matches better.
  return !siblings.some((s) => s !== item && s.href.length > item.href.length && (pathname === s.href || pathname.startsWith(s.href + "/")));
}

/** Role-aware sidebar built from lib/nav.ts. `collapsed` shows the 72px icon rail (desktop only). */
export function AppSidebar({ collapsed = false, onNavigate }: { collapsed?: boolean; onNavigate?: () => void }) {
  const { role } = useAuth();
  const pathname = usePathname();
  if (!role) return null;
  const groups = navFor(role);
  const all = groups.flatMap((g) => g.items);

  return (
    <div className="flex h-full flex-col bg-sidebar text-sidebar-foreground">
      <div className={cn("flex h-14 shrink-0 items-center border-b border-sidebar-border", collapsed ? "justify-center px-2" : "px-5")}>
        <Logo href={roleHome(role)} collapsed={collapsed} />
      </div>
      <ScrollArea className="flex-1">
        <nav aria-label="Main" className={cn("space-y-5 py-4", collapsed ? "px-2" : "px-3")}>
          {groups.map((g) => (
            <div key={g.label} className="space-y-1">
              {!collapsed && <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/80">{g.label}</p>}
              {collapsed && <div className="mx-auto h-px w-6 bg-sidebar-border first:hidden" />}
              {g.items.map((item) => {
                const active = isActive(item, pathname, all);
                const link = (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "group flex items-center gap-3 rounded-xl text-sm font-medium outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/50",
                      collapsed ? "size-10 justify-center" : "px-3 py-2",
                      active
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                    )}
                  >
                    <item.icon className={cn("size-[18px] shrink-0", active && "text-primary")} />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                    {!collapsed && active && <span className="ml-auto size-1.5 rounded-full bg-primary" />}
                  </Link>
                );
                return collapsed ? (
                  <Tooltip key={item.href}>
                    <TooltipTrigger asChild>{link}</TooltipTrigger>
                    <TooltipContent side="right">{item.label}</TooltipContent>
                  </Tooltip>
                ) : (
                  link
                );
              })}
            </div>
          ))}
        </nav>
      </ScrollArea>
      {!collapsed && (
        <div className="shrink-0 border-t border-sidebar-border p-3">
          <div className="rounded-xl bg-gradient-to-br from-indigo-500/10 to-violet-500/10 p-3 text-xs">
            <p className="font-semibold">{ROLE_LABELS[role]} workspace</p>
            <p className="mt-0.5 text-muted-foreground">Press Ctrl+K to search or jump anywhere.</p>
          </div>
        </div>
      )}
    </div>
  );
}
