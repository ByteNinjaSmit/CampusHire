import { z } from "zod";
import { fullNameSchema, gpaSchema, optionalPhoneSchema, optionalText, optionalUrlSchema } from "./common";

export const userProfileSchema = z.object({
  full_name: fullNameSchema,
  phone: optionalPhoneSchema,
});
export type UserProfileInput = z.input<typeof userProfileSchema>;

export const studentProfileSchema = z.object({
  department: z.string().trim().min(2, { error: "Department is required" }).max(80),
  gpa: gpaSchema,
  graduation_year: z.number().int().min(2000, { error: "Year must be 2000-2100" }).max(2100, { error: "Year must be 2000-2100" }).optional(),
  skills: z.array(z.string().trim().min(1).max(40)).max(40, { error: "Up to 40 skills" }),
  bio: optionalText(2000),
  linkedin_url: optionalUrlSchema,
  github_url: optionalUrlSchema,
  portfolio_url: optionalUrlSchema,
});
export type StudentProfileFormInput = z.input<typeof studentProfileSchema>;
export type StudentProfileFormOutput = z.output<typeof studentProfileSchema>;

export const facultyProfileSchema = z.object({
  department: z.string().trim().min(2, { error: "Department is required" }).max(80),
  designation: optionalText(80),
});
export type FacultyProfileFormInput = z.input<typeof facultyProfileSchema>;
