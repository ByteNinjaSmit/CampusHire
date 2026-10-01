"use client";

import { Briefcase, CornerDownLeft, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
  Command,
} from "@/components/ui/command";
import { useDebouncedValue } from "@/components/shared/SearchInput";
import { useInternships } from "@/lib/api/hooks/internships";
import { flatNavFor, QUICK_ACTIONS } from "@/lib/nav";
import { useAuth } from "@/providers/AuthProvider";

export const OPEN_PALETTE_EVENT = "campushire:open-palette";

export function openCommandPalette() {
  window.dispatchEvent(new Event(OPEN_PALETTE_EVENT));
}

/** Ctrl/Cmd+K palette: role navigation, quick actions, debounced internship search (/internships?q=). [EXT] */
export function CommandPalette() {
  const router = useRouter();
  const { role } = useAuth();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const debounced = useDebouncedValue(query.trim(), 300);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    const onOpen = () => setOpen(true);
    window.addEventListener("keydown", onKey);
    window.addEventListener(OPEN_PALETTE_EVENT, onOpen);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener(OPEN_PALETTE_EVENT, onOpen);
    };
  }, []);

  const searching = open && debounced.length >= 2;
  const results = useInternships({ q: debounced, page_size: 5, sort: "relevance" }, searching);

  const go = useCallback(
    (href: string) => {
      setOpen(false);
      setQuery("");
      router.push(href);
    },
    [router],
  );

  const q = query.trim().toLowerCase();
  const nav = useMemo(() => (role ? flatNavFor(role) : []), [role]);
  const navMatches = nav.filter((i) => !q || i.label.toLowerCase().includes(q) || i.keywords?.some((k) => k.includes(q)));
  const actions = (role ? QUICK_ACTIONS[role] : []).filter((a) => !q || a.label.toLowerCase().includes(q));

  if (!role) return null;

  return (
    <CommandDialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) setQuery("");
      }}
      title="Command palette"
      description="Search pages, actions and internships"
      className="sm:max-w-xl"
    >
      <Command shouldFilter={false} className="rounded-2xl">
        <CommandInput value={query} onValueChange={setQuery} placeholder="Search pages, actions, internships..." data-testid="command-input" />
        <CommandList className="max-h-[420px]">
          <CommandEmpty>No results found.</CommandEmpty>

          {debounced.length >= 2 && (
            <>
              <CommandGroup heading="Internships">
                {results.isLoading && <div className="px-3 py-2 text-xs text-muted-foreground">Searching...</div>}
                {results.data?.items.map((i) => (
                  <CommandItem key={i.id} value={`internship-${i.id}`} onSelect={() => go(`/internships/${i.id}`)}>
                    <Briefcase />
                    <span className="min-w-0 flex-1 truncate">
                      {i.title} <span className="text-muted-foreground">at {i.company.name}</span>
                    </span>
                  </CommandItem>
                ))}
                <CommandItem value="search-all" onSelect={() => go(`/internships?q=${encodeURIComponent(debounced)}`)}>
                  <Search />
                  <span className="flex-1">Search all internships for &ldquo;{debounced}&rdquo;</span>
                  <CommandShortcut>
                    <CornerDownLeft className="size-3" />
                  </CommandShortcut>
                </CommandItem>
              </CommandGroup>
              <CommandSeparator />
            </>
          )}

          {actions.length > 0 && (
            <CommandGroup heading="Quick actions">
              {actions.map((a) => (
                <CommandItem key={a.href + a.label} value={`action-${a.label}`} onSelect={() => go(a.href)}>
                  <a.icon />
                  {a.label}
                </CommandItem>
              ))}
            </CommandGroup>
          )}

          {navMatches.length > 0 && (
            <CommandGroup heading="Go to">
              {navMatches.map((i) => (
                <CommandItem key={i.href} value={`nav-${i.href}`} onSelect={() => go(i.href)}>
                  <i.icon />
                  {i.label}
                </CommandItem>
              ))}
            </CommandGroup>
          )}
        </CommandList>
      </Command>
    </CommandDialog>
  );
}
