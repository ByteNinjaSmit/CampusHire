"use client";

import { format, isValid, parse, parseISO } from "date-fns";
import { CalendarIcon } from "lucide-react";
import { useState } from "react";
import type { DateRange, Matcher } from "react-day-picker";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

const ISO = "yyyy-MM-dd";
const LOCAL = "yyyy-MM-dd'T'HH:mm";

/** Single date; value is a YYYY-MM-DD string ("" when empty). */
export function DatePicker({
  value,
  onChange,
  placeholder = "Pick a date",
  disabled,
  disabledDates,
  className,
  id,
  invalid,
}: {
  value?: string;
  onChange: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
  disabledDates?: Matcher | Matcher[];
  className?: string;
  id?: string;
  invalid?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const date = value ? parse(value, ISO, new Date()) : undefined;
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          type="button"
          variant="outline"
          disabled={disabled}
          aria-invalid={invalid}
          className={cn("h-10 w-full justify-start rounded-xl px-3 font-normal", !date && "text-muted-foreground", className)}
        >
          <CalendarIcon className="size-4" />
          {date && isValid(date) ? format(date, "dd MMM yyyy") : placeholder}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto rounded-2xl p-0" align="start">
        <Calendar
          mode="single"
          selected={date && isValid(date) ? date : undefined}
          onSelect={(d) => {
            if (d) {
              onChange(format(d, ISO));
              setOpen(false);
            }
          }}
          disabled={disabledDates}
          captionLayout="dropdown"
          autoFocus
        />
      </PopoverContent>
    </Popover>
  );
}

/** Date + time; value is a datetime-local string "yyyy-MM-ddTHH:mm" in the browser's zone (use fromDateTimeLocal to convert to ISO UTC). */
export function DateTimePicker({
  value,
  onChange,
  placeholder = "Pick date and time",
  disabled,
  disabledDates,
  className,
  id,
  invalid,
}: {
  value?: string;
  onChange: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
  disabledDates?: Matcher | Matcher[];
  className?: string;
  id?: string;
  invalid?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const date = value ? parseISO(value) : undefined;
  const valid = date && isValid(date);
  const time = valid ? format(date, "HH:mm") : "09:00";

  const commit = (d: Date, t: string) => {
    const [h, m] = t.split(":").map(Number);
    const next = new Date(d.getFullYear(), d.getMonth(), d.getDate(), Number.isFinite(h) ? h : 9, Number.isFinite(m) ? m : 0);
    onChange(format(next, LOCAL));
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          type="button"
          variant="outline"
          disabled={disabled}
          aria-invalid={invalid}
          className={cn("h-10 w-full justify-start rounded-xl px-3 font-normal", !valid && "text-muted-foreground", className)}
        >
          <CalendarIcon className="size-4" />
          {valid ? format(date, "dd MMM yyyy, h:mm a") : placeholder}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto rounded-2xl p-0" align="start">
        <Calendar
          mode="single"
          selected={valid ? date : undefined}
          onSelect={(d) => d && commit(d, time)}
          disabled={disabledDates}
          captionLayout="dropdown"
          autoFocus
        />
        <div className="flex items-center gap-2 border-t p-3">
          <label htmlFor={`${id ?? "dt"}-time`} className="text-sm font-medium">
            Time
          </label>
          <Input
            id={`${id ?? "dt"}-time`}
            type="time"
            value={time}
            onChange={(e) => commit(valid ? date : new Date(), e.target.value)}
            className="h-9 w-32 rounded-lg"
          />
          <Button type="button" size="sm" className="ml-auto rounded-lg" onClick={() => setOpen(false)}>
            Done
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}

export interface DateRangeValue {
  from?: string;
  to?: string;
}

/** Date range; values are YYYY-MM-DD strings. */
export function DateRangePicker({
  value,
  onChange,
  placeholder = "Pick a date range",
  className,
  disabled,
}: {
  value?: DateRangeValue;
  onChange: (v: DateRangeValue) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}) {
  const from = value?.from ? parse(value.from, ISO, new Date()) : undefined;
  const to = value?.to ? parse(value.to, ISO, new Date()) : undefined;
  const selected: DateRange | undefined = from && isValid(from) ? { from, to: to && isValid(to) ? to : undefined } : undefined;
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
          className={cn("h-10 justify-start rounded-xl px-3 font-normal", !selected && "text-muted-foreground", className)}
        >
          <CalendarIcon className="size-4" />
          {selected?.from
            ? selected.to
              ? `${format(selected.from, "dd MMM yyyy")} - ${format(selected.to, "dd MMM yyyy")}`
              : format(selected.from, "dd MMM yyyy")
            : placeholder}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto rounded-2xl p-0" align="start">
        <Calendar
          mode="range"
          numberOfMonths={2}
          selected={selected}
          onSelect={(r) => onChange({ from: r?.from ? format(r.from, ISO) : undefined, to: r?.to ? format(r.to, ISO) : undefined })}
          autoFocus
        />
        {(value?.from || value?.to) && (
          <div className="flex justify-end border-t p-2">
            <Button type="button" variant="ghost" size="sm" onClick={() => onChange({})}>
              Clear
            </Button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}
