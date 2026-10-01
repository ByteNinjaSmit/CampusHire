import { z } from "zod";
import { optionalText, ratingSchema } from "./common";

export const studentFeedbackSchema = z.object({
  application_id: z.string().min(1),
  company_culture: ratingSchema,
  mentorship: ratingSchema,
  technical_learning: ratingSchema,
  work_environment: ratingSchema,
  overall: ratingSchema,
  comments: optionalText(3000),
  suggestions: optionalText(3000),
  is_anonymous: z.boolean().optional(),
});
export type StudentFeedbackInput = z.input<typeof studentFeedbackSchema>;

export const companyFeedbackSchema = z.object({
  application_id: z.string().min(1),
  technical_skills: ratingSchema,
  soft_skills: ratingSchema,
  punctuality: ratingSchema,
  responsibility: ratingSchema,
  teamwork: ratingSchema,
  learning_ability: ratingSchema,
  hire_likelihood: ratingSchema,
  strengths: optionalText(3000),
  improvements: optionalText(3000),
});
export type CompanyFeedbackInput = z.input<typeof companyFeedbackSchema>;

export const facultyFeedbackSchema = z.object({
  internship_id: z.string().min(1, { error: "Choose an internship" }),
  application_id: z.string().optional(),
  course_suitability: ratingSchema,
  learning_outcomes: ratingSchema,
  internship_quality: ratingSchema,
  suggestions: optionalText(3000),
  comments: optionalText(3000),
});
export type FacultyFeedbackInput = z.input<typeof facultyFeedbackSchema>;

export const systemFeedbackSchema = z
  .object({
    type: z.enum(["FEATURE", "BUG", "IMPROVEMENT"], { error: "Choose a type" }),
    title: z.string().trim().min(3, { error: "Title must be at least 3 characters" }).max(160),
    description: z.string().trim().min(10, { error: "Please describe it in at least 10 characters" }).max(5000),
    page_url: optionalText(500),
    severity: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]).optional(),
  })
  .superRefine((v, ctx) => {
    if (v.type === "BUG" && !v.severity) ctx.addIssue({ code: "custom", path: ["severity"], message: "Choose a severity for bugs" });
  });
export type SystemFeedbackInput = z.input<typeof systemFeedbackSchema>;

export const respondSchema = z.object({ body: z.string().trim().min(2, { error: "Write a response" }).max(3000) });
