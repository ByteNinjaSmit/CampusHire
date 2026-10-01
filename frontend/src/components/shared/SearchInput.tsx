"use client";

import { Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

/** Debounced search box. `onSearch` fires after `delay` ms of silence (and on Enter). */
export function SearchInput({
  value,
  onSearch,
  placeholder = "Search...",
  delay = 300,
  className,
  autoFocus,
  "aria-label": ariaLabel,
}: {
  value?: string;
  onSearch: (q: string) => void;
  placeholder?: string;
  delay?: number;
  className?: string;
  autoFocus?: boolean;
  "aria-label"?: string;
}) {
  const [text, setText] = useState(value ?? "");
  const last = useRef(value ?? "");

  // Sync external changes (e.g. URL-driven state).
  useEffect(() => {
    if (value !== undefined && value !== last.current) {
      last.current = value;
      setText(value);
    }
  }, [value]);

  useEffect(() => {
    if (text === last.current) return;
    const t = setTimeout(() => {
      last.current = text;
      onSearch(text);
    }, delay);
    return () => clearTimeout(t);
  }, [text, delay, onSearch]);

  return (
    <div className={cn("relative", className)}>
      <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        type="search"
        value={text}
        autoFocus={autoFocus}
        aria-label={ariaLabel ?? placeholder}
        placeholder={placeholder}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            last.current = text;
            onSearch(text);
          }
        }}
        className="h-10 rounded-xl pl-9 pr-9 [&::-webkit-search-cancel-button]:hidden"
      />
      {text && (
        <button
          type="button"
          aria-label="Clear search"
          className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          onClick={() => {
            setText("");
            last.current = "";
            onSearch("");
          }}
        >
          <X className="size-3.5" />
        </button>
      )}
    </div>
  );
}
