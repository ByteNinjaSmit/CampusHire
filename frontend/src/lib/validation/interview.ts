import { z } from "zod";
import { emailSchema } from "./common";

export const MIN_NOTICE_MS = 24 * 3_600_000;

/**
 * Interview scheduling rules (PLAN 3.9):
 *  R1: scheduled_at >= now + 24h
 *  R2: scheduled_at + duration <= internship.application_deadline (our reading of the spec)
 *  R5: ONLINE needs meeting_link, ONSITE needs location
 */
export function makeInterviewSchema(applicationDeadline?: string | null) {
  return z
    .object({
      application_id: z.string().optional(),
      scheduled_at: z.string({ error: "Pick a date and time" }).min(1, { error: "Pick a date and time" }),
      duration_minutes: z
        .number({ error: "Duration is required" })
        .int()
        .min(15, { error: "At least 15 minutes" })
        .max(240, { error: "At most 240 minutes" }),
      mode: z.enum(["ONLINE", "ONSITE", "PHONE"], { error: "Choose a mode" }),
      location: z.string().trim().optional(),
      meeting_link: z.string().trim().optional(),
      interviewer_name: z.string().trim().min(2, { error: "Interviewer name is required" }).max(120),
      interviewer_email: z
        .string()
        .trim()
        .optional()
        .transform((v) => (v ? v.toLowerCase() : undefined))
        .refine((v) => v === undefined || emailSchema.safeParse(v).success, { error: "Enter a valid email address" }),
    })
    .superRefine((v, ctx) => {
      const add = (path: string, message: string) => ctx.addIssue({ code: "custom", path: [path], message });
      const at = new Date(v.scheduled_at).getTime();
      if (Number.isNaN(at)) {
        add("scheduled_at", "Enter a valid date and time");
      } else {
        if (at < Date.now() + MIN_NOTICE_MS) add("scheduled_at", "Interviews need at least 24 hours notice");
        if (applicationDeadline) {
          const end = at + (v.duration_minutes || 0) * 60_000;
          if (end > new Date(applicationDeadline).getTime()) {
            add("scheduled_at", "Interview must finish before the internship application deadline");
          }
        }
      }
      if (v.mode === "ONLINE" && !v.meeting_link) add("meeting_link", "A meeting link is required for online interviews");
      if (v.mode === "ONSITE" && !v.location) add("location", "A location is required for onsite interviews");
    });
}

export const interviewSchema = makeInterviewSchema();
export type InterviewFormInput = z.input<typeof interviewSchema>;
export type InterviewFormOutput = z.output<typeof interviewSchema>;

export function makeRescheduleSchema(applicationDeadline?: string | null) {
  return z
    .object({
      scheduled_at: z.string().min(1, { error: "Pick a date and time" }),
      duration_minutes: z.number().int().min(15).max(240).optional(),
      reason: z.string().trim().min(3, { error: "Please give a reason" }).max(500),
    })
    .superRefine((v, ctx) => {
      const at = new Date(v.scheduled_at).getTime();
      if (Number.isNaN(at)) return ctx.addIssue({ code: "custom", path: ["scheduled_at"], message: "Enter a valid date and time" });
      if (at < Date.now() + MIN_NOTICE_MS)
        ctx.addIssue({ code: "custom", path: ["scheduled_at"], message: "Interviews need at least 24 hours notice" });
      if (applicationDeadline && at + (v.duration_minutes ?? 30) * 60_000 > new Date(applicationDeadline).getTime())
        ctx.addIssue({ code: "custom", path: ["scheduled_at"], message: "Interview must finish before the application deadline" });
    });
}
