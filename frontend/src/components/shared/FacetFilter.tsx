"use client";

import { Check, ChevronDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export interface FacetOption {
  value: string;
  label?: string;
  count?: number;
}

/** Multi-select popover with search (company combobox, domain, location...). */
export function FacetFilter({
  label,
  options,
  selected,
  onChange,
  searchable = true,
  className,
  single,
}: {
  label: string;
  options: FacetOption[];
  selected: string[];
  onChange: (values: string[]) => void;
  searchable?: boolean;
  className?: string;
  /** Single-select behaviour (acts as a combobox). */
  single?: boolean;
}) {
  const toggle = (v: string) => {
    if (single) return onChange(selected.includes(v) ? [] : [v]);
    onChange(selected.includes(v) ? selected.filter((s) => s !== v) : [...selected, v]);
  };
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" className={cn("h-10 justify-between gap-2 rounded-xl font-normal", className)} aria-label={`Filter by ${label}`}>
          <span className="flex items-center gap-2">
            {label}
            {selected.length > 0 && (
              <Badge variant="secondary" className="rounded-md px-1.5 tabular-nums">
                {selected.length}
              </Badge>
            )}
          </span>
          <ChevronDown className="size-4 opacity-60" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-64 rounded-2xl p-0">
        <Command>
          {searchable && <CommandInput placeholder={`Search ${label.toLowerCase()}...`} />}
          <CommandList>
            <CommandEmpty>No results.</CommandEmpty>
            <CommandGroup>
              {options.map((o) => {
                const isSel = selected.includes(o.value);
                return (
                  <CommandItem key={o.value} value={o.label ?? o.value} onSelect={() => toggle(o.value)}>
                    <span className={cn("mr-2 flex size-4 items-center justify-center rounded border", isSel ? "border-primary bg-primary text-primary-foreground" : "border-input")}>
                      {isSel && <Check className="size-3" />}
                    </span>
                    <span className="flex-1 truncate">{o.label ?? o.value}</span>
                    {o.count !== undefined && <span className="text-xs tabular-nums text-muted-foreground">{o.count}</span>}
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </CommandList>
          {selected.length > 0 && (
            <div className="border-t p-1">
              <Button variant="ghost" size="sm" className="w-full" onClick={() => onChange([])}>
                Clear
              </Button>
            </div>
          )}
        </Command>
      </PopoverContent>
    </Popover>
  );
}
