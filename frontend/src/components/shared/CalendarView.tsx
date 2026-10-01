"use client";

import {
  addDays,
  addMonths,
  addWeeks,
  differenceInMinutes,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  isToday,
  parseISO,
  startOfDay,
  startOfMonth,
  startOfWeek,
} from "date-fns";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { COLOR_CLASSES, type StatusColor } from "@/lib/status";
import { cn } from "@/lib/utils";

export interface CalendarEvent<T = unknown> {
  id: string;
  title: string;
  start: string | Date;
  end?: string | Date;
  color?: StatusColor;
  meta?: T;
}

const toDate = (v: string | Date) => (typeof v === "string" ? parseISO(v) : v);
const HOUR_PX = 48;

/** Custom month/week calendar built on date-fns (no external calendar lib). */
export function CalendarView<T = unknown>({
  events,
  view: viewProp,
  onViewChange,
  date: dateProp,
  onDateChange,
  onSelectEvent,
  onSelectSlot,
  startHour = 7,
  endHour = 21,
  className,
}: {
  events: CalendarEvent<T>[];
  view?: "month" | "week";
  onViewChange?: (v: "month" | "week") => void;
  date?: Date;
  onDateChange?: (d: Date) => void;
  onSelectEvent?: (e: CalendarEvent<T>) => void;
  onSelectSlot?: (slot: Date) => void;
  startHour?: number;
  endHour?: number;
  className?: string;
}) {
  const [viewState, setViewState] = useState<"month" | "week">("month");
  const [dateState, setDateState] = useState(() => new Date());
  const view = viewProp ?? viewState;
  const cursor = dateProp ?? dateState;
  const setView = (v: "month" | "week") => (onViewChange ? onViewChange(v) : setViewState(v));
  const setCursor = (d: Date) => (onDateChange ? onDateChange(d) : setDateState(d));

  const parsed = useMemo(
    () => events.map((e) => ({ ...e, s: toDate(e.start), e: e.end ? toDate(e.end) : addDays(toDate(e.start), 0) })),
    [events],
  );

  const monthDays = useMemo(
    () => eachDayOfInterval({ start: startOfWeek(startOfMonth(cursor), { weekStartsOn: 1 }), end: endOfWeek(endOfMonth(cursor), { weekStartsOn: 1 }) }),
    [cursor],
  );
  const weekDays = useMemo(
    () => eachDayOfInterval({ start: startOfWeek(cursor, { weekStartsOn: 1 }), end: endOfWeek(cursor, { weekStartsOn: 1 }) }),
    [cursor],
  );

  const step = (dir: 1 | -1) => setCursor(view === "month" ? addMonths(cursor, dir) : addWeeks(cursor, dir));
  const label = view === "month" ? format(cursor, "MMMM yyyy") : `${format(weekDays[0], "d MMM")} - ${format(weekDays[6], "d MMM yyyy")}`;
  const hours = Array.from({ length: endHour - startHour + 1 }, (_, i) => startHour + i);

  return (
    <div className={cn("card-surface overflow-hidden", className)}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b p-3">
        <div className="flex items-center gap-1.5">
          <Button variant="outline" size="icon-sm" aria-label="Previous" onClick={() => step(-1)}>
            <ChevronLeft />
          </Button>
          <Button variant="outline" size="icon-sm" aria-label="Next" onClick={() => step(1)}>
            <ChevronRight />
          </Button>
          <Button variant="outline" size="sm" className="rounded-lg" onClick={() => setCursor(new Date())}>
            Today
          </Button>
          <h3 className="ml-2 text-base font-semibold" aria-live="polite">
            {label}
          </h3>
        </div>
        <ToggleGroup type="single" variant="outline" size="sm" value={view} onValueChange={(v) => v && setView(v as "month" | "week")}>
          <ToggleGroupItem value="month">Month</ToggleGroupItem>
          <ToggleGroupItem value="week">Week</ToggleGroupItem>
        </ToggleGroup>
      </div>

      {view === "month" ? (
        <div>
          <div className="grid grid-cols-7 border-b bg-muted/30 text-center text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {weekDays.map((d) => (
              <div key={d.toISOString()} className="py-2">
                {format(d, "EEE")}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {monthDays.map((day) => {
              const dayEvents = parsed.filter((e) => isSameDay(e.s, day)).sort((a, b) => a.s.getTime() - b.s.getTime());
              return (
                <div
                  key={day.toISOString()}
                  role="gridcell"
                  tabIndex={0}
                  onClick={() => onSelectSlot?.(startOfDay(day))}
                  onKeyDown={(e) => e.key === "Enter" && onSelectSlot?.(startOfDay(day))}
                  className={cn(
                    "min-h-24 border-b border-r p-1.5 text-left outline-none transition-colors hover:bg-muted/40 focus-visible:bg-muted/40 md:min-h-28",
                    !isSameMonth(day, cursor) && "bg-muted/20 text-muted-foreground/60",
                    onSelectSlot && "cursor-pointer",
                  )}
                >
                  <span
                    className={cn(
                      "inline-flex size-6 items-center justify-center rounded-full text-xs font-medium",
                      isToday(day) && "bg-primary text-primary-foreground",
                    )}
                  >
                    {format(day, "d")}
                  </span>
                  <div className="mt-1 space-y-0.5">
                    {dayEvents.slice(0, 3).map((e) => (
                      <EventChip key={e.id} event={e} onClick={onSelectEvent} />
                    ))}
                    {dayEvents.length > 3 && <p className="px-1 text-[11px] text-muted-foreground">+{dayEvents.length - 3} more</p>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <div className="min-w-[640px]">
            <div className="grid grid-cols-[48px_repeat(7,1fr)] border-b bg-muted/30 text-center text-xs">
              <div />
              {weekDays.map((d) => (
                <div key={d.toISOString()} className="py-2">
                  <p className="font-medium uppercase tracking-wide text-muted-foreground">{format(d, "EEE")}</p>
                  <p className={cn("mx-auto mt-0.5 flex size-7 items-center justify-center rounded-full text-sm font-semibold", isToday(d) && "bg-primary text-primary-foreground")}>
                    {format(d, "d")}
                  </p>
                </div>
              ))}
            </div>
            <div className="grid max-h-[600px] grid-cols-[48px_repeat(7,1fr)] overflow-y-auto">
              <div>
                {hours.map((h) => (
                  <div key={h} style={{ height: HOUR_PX }} className="pr-1 text-right text-[11px] text-muted-foreground">
                    <span className="relative -top-2">{format(new Date(2000, 0, 1, h), "h a")}</span>
                  </div>
                ))}
              </div>
              {weekDays.map((day) => {
                const dayEvents = parsed.filter((e) => isSameDay(e.s, day));
                return (
                  <div key={day.toISOString()} className="relative border-l">
                    {hours.map((h) => (
                      <div
                        key={h}
                        style={{ height: HOUR_PX }}
                        role="gridcell"
                        onClick={() => onSelectSlot?.(new Date(day.getFullYear(), day.getMonth(), day.getDate(), h))}
                        className={cn("border-b hover:bg-muted/40", onSelectSlot && "cursor-pointer")}
                      />
                    ))}
                    {dayEvents.map((e) => {
                      const startMin = e.s.getHours() * 60 + e.s.getMinutes() - startHour * 60;
                      const dur = Math.max(30, e.end ? differenceInMinutes(e.e, e.s) : 30);
                      const c = COLOR_CLASSES[e.color ?? "indigo"];
                      return (
                        <button
                          key={e.id}
                          type="button"
                          onClick={(ev) => {
                            ev.stopPropagation();
                            onSelectEvent?.(e);
                          }}
                          style={{ top: Math.max(0, (startMin / 60) * HOUR_PX), height: (dur / 60) * HOUR_PX - 2 }}
                          className={cn("absolute inset-x-0.5 overflow-hidden rounded-lg px-1.5 py-1 text-left text-[11px] leading-tight ring-1 ring-inset", c.badge)}
                        >
                          <span className="block truncate font-semibold">{e.title}</span>
                          <span className="block truncate opacity-80">{format(e.s, "h:mm a")}</span>
                        </button>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function EventChip<T>({
  event,
  onClick,
}: {
  event: CalendarEvent<T> & { s: Date };
  onClick?: (e: CalendarEvent<T>) => void;
}) {
  const c = COLOR_CLASSES[event.color ?? "indigo"];
  return (
    <button
      type="button"
      title={event.title}
      onClick={(ev) => {
        ev.stopPropagation();
        onClick?.(event);
      }}
      className={cn("flex w-full items-center gap-1 truncate rounded-md px-1.5 py-0.5 text-left text-[11px] font-medium ring-1 ring-inset", c.badge)}
    >
      <span className="shrink-0 opacity-80">{format(event.s, "h:mma").toLowerCase()}</span>
      <span className="truncate">{event.title}</span>
    </button>
  );
}
