// Status labels and colors (PLAN 5.2). Class strings are static so Tailwind can see them.
export type StatusColor =
  | "slate" | "sky" | "violet" | "amber" | "emerald" | "rose" | "zinc" | "indigo" | "cyan" | "orange";

export const COLOR_CLASSES: Record<StatusColor, { badge: string; dot: string; solid: string; text: string }> = {
  slate: { badge: "bg-slate-500/10 text-slate-600 dark:text-slate-400 ring-slate-500/20", dot: "bg-slate-500", solid: "bg-slate-500", text: "text-slate-600 dark:text-slate-400" },
  sky: { badge: "bg-sky-500/10 text-sky-600 dark:text-sky-400 ring-sky-500/20", dot: "bg-sky-500", solid: "bg-sky-500", text: "text-sky-600 dark:text-sky-400" },
  violet: { badge: "bg-violet-500/10 text-violet-600 dark:text-violet-400 ring-violet-500/20", dot: "bg-violet-500", solid: "bg-violet-500", text: "text-violet-600 dark:text-violet-400" },
  amber: { badge: "bg-amber-500/10 text-amber-600 dark:text-amber-400 ring-amber-500/20", dot: "bg-amber-500", solid: "bg-amber-500", text: "text-amber-600 dark:text-amber-400" },
  emerald: { badge: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 ring-emerald-500/20", dot: "bg-emerald-500", solid: "bg-emerald-500", text: "text-emerald-600 dark:text-emerald-400" },
  rose: { badge: "bg-rose-500/10 text-rose-600 dark:text-rose-400 ring-rose-500/20", dot: "bg-rose-500", solid: "bg-rose-500", text: "text-rose-600 dark:text-rose-400" },
  zinc: { badge: "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 ring-zinc-500/20", dot: "bg-zinc-500", solid: "bg-zinc-500", text: "text-zinc-600 dark:text-zinc-400" },
  indigo: { badge: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 ring-indigo-500/20", dot: "bg-indigo-500", solid: "bg-indigo-500", text: "text-indigo-600 dark:text-indigo-400" },
  cyan: { badge: "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 ring-cyan-500/20", dot: "bg-cyan-500", solid: "bg-cyan-500", text: "text-cyan-600 dark:text-cyan-400" },
  orange: { badge: "bg-orange-500/10 text-orange-600 dark:text-orange-400 ring-orange-500/20", dot: "bg-orange-500", solid: "bg-orange-500", text: "text-orange-600 dark:text-orange-400" },
};

interface StatusMeta { label: string; color: StatusColor }

/**
 * Generic status table across all domains. Overlapping names (PENDING, REJECTED) have one meaning per color here;
 * pass `kind` to StatusBadge when a domain needs a different label.
 */
export const STATUS_META: Record<string, StatusMeta> = {
  // applications (UNDER_REVIEW / INTERVIEW are sub-states of pending / shortlisted in the UI copy)
  PENDING: { label: "Pending", color: "slate" },
  UNDER_REVIEW: { label: "Under review", color: "sky" },
  SHORTLISTED: { label: "Shortlisted", color: "violet" },
  INTERVIEW: { label: "Interview", color: "amber" },
  ACCEPTED: { label: "Accepted", color: "emerald" },
  REJECTED: { label: "Rejected", color: "rose" },
  WITHDRAWN: { label: "Withdrawn", color: "zinc" },
  // internships
  DRAFT: { label: "Draft", color: "zinc" },
  PENDING_APPROVAL: { label: "Pending approval", color: "amber" },
  APPROVED: { label: "Approved", color: "emerald" },
  CLOSED: { label: "Closed", color: "slate" },
  // companies
  ACTIVE: { label: "Active", color: "emerald" },
  ARCHIVED: { label: "Archived", color: "zinc" },
  // interviews
  SCHEDULED: { label: "Scheduled", color: "sky" },
  RESCHEDULED: { label: "Rescheduled", color: "amber" },
  COMPLETED: { label: "Completed", color: "emerald" },
  CANCELLED: { label: "Cancelled", color: "zinc" },
  NO_SHOW: { label: "No show", color: "rose" },
  PASS: { label: "Pass", color: "emerald" },
  FAIL: { label: "Fail", color: "rose" },
  ON_HOLD: { label: "On hold", color: "amber" },
  // documents
  PENDING_UPLOAD: { label: "Uploading", color: "slate" },
  UPLOADED: { label: "Uploaded", color: "sky" },
  VERIFIED: { label: "Verified", color: "emerald" },
  // jobs
  QUEUED: { label: "Queued", color: "slate" },
  RUNNING: { label: "Running", color: "sky" },
  SUCCEEDED: { label: "Succeeded", color: "emerald" },
  FAILED: { label: "Failed", color: "rose" },
  // compliance
  OPEN: { label: "Open", color: "amber" },
  RESOLVED: { label: "Resolved", color: "emerald" },
  DISMISSED: { label: "Dismissed", color: "zinc" },
  // system feedback
  NEW: { label: "New", color: "indigo" },
  TRIAGED: { label: "Triaged", color: "sky" },
  PLANNED: { label: "Planned", color: "violet" },
  IN_PROGRESS: { label: "In progress", color: "amber" },
  DONE: { label: "Done", color: "emerald" },
  WONT_DO: { label: "Won't do", color: "zinc" },
  // severity / priority
  LOW: { label: "Low", color: "slate" },
  MEDIUM: { label: "Medium", color: "amber" },
  HIGH: { label: "High", color: "orange" },
  CRITICAL: { label: "Critical", color: "rose" },
  // recommendations
  STRONG_YES: { label: "Strong yes", color: "emerald" },
  YES: { label: "Yes", color: "cyan" },
  MAYBE: { label: "Maybe", color: "amber" },
  NO: { label: "No", color: "rose" },
  // roles
  ADMIN: { label: "Admin", color: "rose" },
  FACULTY: { label: "Faculty", color: "violet" },
  STUDENT: { label: "Student", color: "indigo" },
  COMPANY: { label: "Company", color: "cyan" },
};

export function statusMeta(status: string): StatusMeta {
  return (
    STATUS_META[status] ?? {
      label: status
        .toLowerCase()
        .split("_")
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" "),
      color: "zinc",
    }
  );
}

export const APPLICATION_STATUS_ORDER = ["PENDING", "UNDER_REVIEW", "SHORTLISTED", "INTERVIEW", "ACCEPTED"] as const;

export const APPLICATION_STATUSES = ["PENDING", "UNDER_REVIEW", "SHORTLISTED", "INTERVIEW", "ACCEPTED", "REJECTED", "WITHDRAWN"] as const;
export const INTERNSHIP_STATUSES = ["DRAFT", "PENDING_APPROVAL", "APPROVED", "REJECTED", "CLOSED"] as const;
export const ROLE_LABELS = { ADMIN: "Administrator", FACULTY: "Faculty", STUDENT: "Student", COMPANY: "Company" } as const;
