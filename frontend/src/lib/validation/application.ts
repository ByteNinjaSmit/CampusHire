import { z } from "zod";
import { optionalText, optionalUrlSchema } from "./common";

export const MAX_RESUME_BYTES = 5 * 1024 * 1024;

/** Per-step schemas for the 5-step application wizard (PLAN 5.4). */
export const resumeStepSchema = z.object({
  resume_document_id: z.string({ error: "A resume is required" }).min(1, { error: "A resume is required" }),
});

export const coverLetterStepSchema = z.object({
  cover_letter: z
    .string({ error: "Cover letter is required" })
    .trim()
    .min(50, { error: "Cover letter must be at least 50 characters" })
    .max(5000, { error: "Cover letter must be at most 5000 characters" }),
});

export const qualificationsStepSchema = z.object({
  qualifications: z
    .string({ error: "Qualifications are required" })
    .trim()
    .min(10, { error: "Qualifications must be at least 10 characters" })
    .max(3000, { error: "Qualifications must be at most 3000 characters" }),
  skills: z.array(z.string().trim().min(1)).max(30).optional(),
  coursework: optionalText(1000),
  availability_from: z
    .string()
    .optional()
    .transform((v) => (v ? v : undefined))
    .refine((v) => v === undefined || /^\d{4}-\d{2}-\d{2}$/.test(v), { error: "Pick a valid date" }),
  portfolio_url: optionalUrlSchema,
});

export const confirmStepSchema = z.object({
  confirm: z.literal(true, { error: "Please confirm that the information is accurate" }),
});

export const applicationSchema = resumeStepSchema.extend(coverLetterStepSchema.shape).extend(qualificationsStepSchema.shape);
export type ApplicationFormInput = z.input<typeof applicationSchema>;

/** Client-side PDF check used by FileUpload (spec V4). */
export function validateResumeFile(file: File, maxBytes = MAX_RESUME_BYTES): string | null {
  if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) return "Only PDF files are allowed";
  if (file.type && file.type !== "application/pdf") return "Only PDF files are allowed";
  if (file.size <= 0) return "The file is empty";
  if (file.size > maxBytes) return `File is too large (max ${Math.round(maxBytes / 1024 / 1024)} MB)`;
  return null;
}
