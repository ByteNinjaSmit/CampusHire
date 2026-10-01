import { z } from "zod";
import { emailSchema, fullNameSchema, optionalPhoneSchema, optionalText, optionalUrlSchema, registrationNumberSchema } from "./common";

export const companySchema = z.object({
  name: z.string().trim().min(2, { error: "Company name is required" }).max(160),
  registration_number: registrationNumberSchema,
  location: z.string().trim().min(2, { error: "Location is required" }).max(160),
  industry: optionalText(80),
  website: optionalUrlSchema,
  description: optionalText(5000),
  contact_person_name: fullNameSchema,
  contact_email: emailSchema,
  contact_phone: optionalPhoneSchema,
});
export type CompanyFormInput = z.input<typeof companySchema>;
export type CompanyFormOutput = z.output<typeof companySchema>;

export const evaluationFormSchema = z.object({
  name: z.string().trim().min(2, { error: "Form name is required" }).max(120),
  description: optionalText(1000),
  criteria: z
    .array(
      z.object({
        name: z.string().trim().min(2, { error: "Criterion name is required" }).max(120),
        description: optionalText(500),
        weight: z.number({ error: "Weight is required" }).gt(0, { error: "Weight must be above 0" }).max(10, { error: "Weight cannot exceed 10" }),
        max_score: z.union([z.literal(5), z.literal(10)]),
      }),
    )
    .min(1, { error: "Add at least one criterion" }),
});
export type EvaluationFormInput = z.input<typeof evaluationFormSchema>;
