import { z } from "zod";

export const INTERNSHIP_DOMAINS = [
  "Software Engineering",
  "Data Science",
  "AI/ML",
  "Cloud & DevOps",
  "Cybersecurity",
  "Product Design",
  "Product Management",
  "Marketing",
  "Finance",
  "Operations",
  "Hardware/Embedded",
  "Research",
] as const;

export const DEPARTMENTS = ["CSE", "IT", "ECE", "EEE", "ME", "CE", "MBA", "BBA", "Other"] as const;

const DAY_MS = 86_400_000;

/** Whole days between two YYYY-MM-DD strings (UTC). */
export function daysBetween(start: string, end: string): number {
  const s = Date.parse(`${start}T00:00:00Z`);
  const e = Date.parse(`${end}T00:00:00Z`);
  return Math.round((e - s) / DAY_MS);
}

export function computeDurationWeeks(start?: string, end?: string): number | null {
  if (!start || !end) return null;
  const d = daysBetween(start, end);
  if (!Number.isFinite(d) || d <= 0) return null;
  return Math.round(d / 7);
}

/** Local "today" as YYYY-MM-DD. */
export function todayISODate(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const dateStr = z.string({ error: "Date is required" }).regex(/^\d{4}-\d{2}-\d{2}$/, { error: "Pick a date" });

export const internshipSchema = z
  .object({
    company_id: z.string({ error: "Company is required" }).min(1, { error: "Company is required" }),
    title: z.string().trim().min(3, { error: "Title must be at least 3 characters" }).max(160),
    description: z.string().trim().min(20, { error: "Describe the role in at least 20 characters" }).max(10000),
    domain: z.string({ error: "Choose a domain" }).min(1, { error: "Choose a domain" }),
    location: z.string().trim().min(2, { error: "Location is required" }).max(160),
    work_mode: z.enum(["ONSITE", "REMOTE", "HYBRID"], { error: "Choose a work mode" }),
    stipend_monthly: z.number({ error: "Stipend is required (0 for unpaid)" }).min(0, { error: "Stipend cannot be negative" }),
    currency: z.string().length(3).optional(),
    start_date: dateStr,
    end_date: dateStr,
    application_deadline: z.string({ error: "Deadline is required" }).min(1, { error: "Deadline is required" }),
    duration_weeks: z.number().int().optional(),
    openings: z.number().int().min(1, { error: "At least 1 opening" }).max(1000).optional(),
    skills: z.array(z.string().trim().min(1)).max(30).optional(),
    min_gpa: z
      .number()
      .min(0, { error: "Min GPA must be between 0 and 4" })
      .max(4, { error: "Min GPA must be between 0 and 4" })
      .nullable()
      .optional(),
    eligible_departments: z.array(z.string()).optional(),
  })
  .superRefine((v, ctx) => {
    const today = todayISODate();
    const add = (path: string, message: string) => ctx.addIssue({ code: "custom", path: [path], message });

    if (v.start_date && v.start_date <= today) add("start_date", "Start date must be in the future");
    if (v.end_date && v.end_date <= today) add("end_date", "End date must be in the future");
    if (v.start_date && v.end_date) {
      if (v.start_date >= v.end_date) {
        add("end_date", "End date must be after the start date");
      } else {
        const days = daysBetween(v.start_date, v.end_date);
        if (days < 28) add("end_date", "Duration must be at least 4 weeks (28 days)");
        else if (days > 183) add("end_date", "Duration cannot exceed 6 months (183 days)");
      }
    }
    if (v.application_deadline) {
      const dl = new Date(v.application_deadline).getTime();
      if (Number.isNaN(dl)) add("application_deadline", "Enter a valid deadline");
      else {
        if (dl <= Date.now()) add("application_deadline", "Deadline must be in the future");
        if (v.start_date && dl >= Date.parse(`${v.start_date}T00:00:00Z`)) {
          add("application_deadline", "Deadline must be before the start date");
        }
      }
    }
    if (v.duration_weeks !== undefined && v.start_date && v.end_date) {
      const computed = computeDurationWeeks(v.start_date, v.end_date);
      if (computed !== null && Math.abs(v.duration_weeks - computed) > 1) {
        add("duration_weeks", `Duration should be about ${computed} weeks for the chosen dates`);
      }
    }
  });
export type InternshipFormInput = z.input<typeof internshipSchema>;
export type InternshipFormOutput = z.output<typeof internshipSchema>;
