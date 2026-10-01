import {
  BadgeCheck,
  CalendarClock,
  CalendarX2,
  CheckCircle2,
  ClipboardCheck,
  Eye,
  Flag,
  RefreshCcw,
  Send,
  Star,
  Undo2,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import type { ApplicationStatus, TimelineEvent } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { COLOR_CLASSES, statusMeta } from "@/lib/status";
import { cn } from "@/lib/utils";

const STATUS_ICON: Record<ApplicationStatus, LucideIcon> = {
  PENDING: Send,
  UNDER_REVIEW: Eye,
  SHORTLISTED: Star,
  INTERVIEW: CalendarClock,
  ACCEPTED: BadgeCheck,
  REJECTED: XCircle,
  WITHDRAWN: Undo2,
};

const KIND_ICON: Record<TimelineEvent["kind"], { icon: LucideIcon; color: keyof typeof COLOR_CLASSES }> = {
  STATUS: { icon: Flag, color: "slate" },
  INTERVIEW_SCHEDULED: { icon: CalendarClock, color: "amber" },
  INTERVIEW_RESCHEDULED: { icon: RefreshCcw, color: "amber" },
  INTERVIEW_CANCELLED: { icon: CalendarX2, color: "zinc" },
  INTERVIEW_COMPLETED: { icon: CheckCircle2, color: "emerald" },
  EVALUATION: { icon: ClipboardCheck, color: "violet" },
  COMPLETED: { icon: BadgeCheck, color: "emerald" },
};

function resolve(e: TimelineEvent) {
  if (e.kind === "STATUS" && e.status) {
    return { icon: STATUS_ICON[e.status] ?? Flag, color: statusMeta(e.status).color };
  }
  return KIND_ICON[e.kind] ?? KIND_ICON.STATUS;
}

/** Vertical timeline with an icon per status/event kind. Newest event last (chronological), as the API returns it. */
export function ApplicationTimeline({ events, className, newestFirst }: { events: TimelineEvent[]; className?: string; newestFirst?: boolean }) {
  const list = newestFirst ? [...events].reverse() : events;
  return (
    <ol className={cn("relative space-y-0", className)}>
      {list.map((e, i) => {
        const { icon: Icon, color } = resolve(e);
        const c = COLOR_CLASSES[color];
        const last = i === list.length - 1;
        return (
          <li key={`${e.at}-${i}`} className="relative flex gap-4 pb-6 last:pb-0">
            {!last && <span className="absolute left-[17px] top-9 h-[calc(100%-2.25rem)] w-px bg-border" aria-hidden />}
            <span className={cn("z-10 flex size-9 shrink-0 items-center justify-center rounded-full ring-1 ring-inset", c.badge)}>
              <Icon className="size-4" />
            </span>
            <div className="min-w-0 flex-1 pt-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <p className="text-sm font-medium">{e.title}</p>
                <time className="text-xs text-muted-foreground" dateTime={e.at}>
                  {formatDateTime(e.at)}
                </time>
              </div>
              {e.note && <p className="mt-1 whitespace-pre-line text-sm text-muted-foreground">{e.note}</p>}
              {e.actor_name && <p className="mt-0.5 text-xs text-muted-foreground">by {e.actor_name}</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
