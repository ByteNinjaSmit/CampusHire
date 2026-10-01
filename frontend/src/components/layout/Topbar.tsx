"use client";

import { Menu, PanelLeftClose, PanelLeftOpen, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NotificationBell } from "./NotificationBell";
import { ThemeToggle } from "./ThemeToggle";
import { UserMenu } from "./UserMenu";
import { openCommandPalette } from "./CommandPalette";

export function Topbar({
  collapsed,
  onToggleCollapsed,
  onOpenMobileNav,
}: {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onOpenMobileNav: () => void;
}) {
  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b bg-background/80 px-3 backdrop-blur supports-[backdrop-filter]:bg-background/60 md:px-6">
      <Button variant="ghost" size="icon" className="rounded-xl md:hidden" aria-label="Open navigation" onClick={onOpenMobileNav}>
        <Menu />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="hidden rounded-xl md:inline-flex"
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        onClick={onToggleCollapsed}
      >
        {collapsed ? <PanelLeftOpen /> : <PanelLeftClose />}
      </Button>

      <button
        type="button"
        onClick={openCommandPalette}
        data-testid="search-trigger"
        aria-label="Open command palette"
        className="group ml-1 flex h-9 w-full max-w-sm items-center gap-2 rounded-xl border bg-muted/40 px-3 text-sm text-muted-foreground transition-colors hover:bg-muted"
      >
        <Search className="size-4" />
        <span className="flex-1 truncate text-left">Search...</span>
        <kbd className="hidden rounded-md border bg-background px-1.5 py-0.5 font-sans text-[11px] font-medium sm:inline">Ctrl K</kbd>
      </button>

      <div className="ml-auto flex items-center gap-1">
        <NotificationBell />
        <ThemeToggle />
        <div className="ml-1.5">
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
