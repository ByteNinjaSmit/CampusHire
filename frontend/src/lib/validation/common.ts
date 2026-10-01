import { z } from "zod";

// ---- password (spec V3): >= 8 chars, upper, lower, digit, special ----
export const PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,128}$/;

export const passwordChecks = [
  { id: "length", label: "At least 8 characters", test: (v: string) => v.length >= 8 && v.length <= 128 },
  { id: "upper", label: "One uppercase letter", test: (v: string) => /[A-Z]/.test(v) },
  { id: "lower", label: "One lowercase letter", test: (v: string) => /[a-z]/.test(v) },
  { id: "digit", label: "One number", test: (v: string) => /\d/.test(v) },
  { id: "special", label: "One special character", test: (v: string) => /[^A-Za-z0-9]/.test(v) },
] as const;

export function passwordStrength(v: string): { score: number; label: "Too weak" | "Weak" | "Fair" | "Good" | "Strong" } {
  const score = passwordChecks.filter((c) => c.test(v)).length;
  const label = (["Too weak", "Too weak", "Weak", "Fair", "Good", "Strong"] as const)[score];
  return { score, label };
}

export const passwordSchema = z
  .string({ error: "Password is required" })
  .regex(PASSWORD_REGEX, {
    error: "Use 8-128 characters with upper and lower case letters, a number and a special character",
  });

// ---- email (spec V1) ----
export const emailSchema = z
  .string({ error: "Email is required" })
  .trim()
  .toLowerCase()
  .pipe(z.email({ error: "Enter a valid email address" }));

// ---- phone (spec V2): 10-15 digits, optional leading +, no leading 0 ----
export const PHONE_REGEX = /^\+?[1-9]\d{9,14}$/;
export const normalizePhoneInput = (v: string) => v.replace(/[\s\-()]/g, "");

export const phoneSchema = z
  .string({ error: "Phone number is required" })
  .trim()
  .transform(normalizePhoneInput)
  .refine((v) => PHONE_REGEX.test(v), { error: "Enter 10-15 digits, optionally starting with +country code" });

/** Empty string -> undefined, otherwise validated like phoneSchema. */
export const optionalPhoneSchema = z
  .string()
  .optional()
  .transform((v) => (v && v.trim() ? normalizePhoneInput(v.trim()) : undefined))
  .refine((v) => v === undefined || PHONE_REGEX.test(v), { error: "Enter 10-15 digits, optionally starting with +country code" });

// ---- GPA (spec V6): 0.0 - 4.0, two decimals max ----
export const gpaSchema = z
  .number({ error: "GPA is required" })
  .refine((v) => Number.isFinite(v), { error: "GPA must be a number" })
  .min(0, { error: "GPA cannot be below 0.0" })
  .max(4, { error: "GPA cannot be above 4.0" })
  .refine((v) => Math.abs(v * 100 - Math.round(v * 100)) < 1e-6, { error: "Use at most 2 decimal places" });

// ---- company registration number (spec V11) ----
export const CIN_REGEX = /^[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$/;
export const INTL_REG_REGEX = /^[A-Z]{2}-[A-Z0-9]{6,15}$/;
export const normalizeRegistrationNumber = (v: string) => v.replace(/\s+/g, "").toUpperCase();

export const registrationNumberSchema = z
  .string({ error: "Registration number is required" })
  .transform(normalizeRegistrationNumber)
  .refine((v) => CIN_REGEX.test(v) || INTL_REG_REGEX.test(v), {
    error: "Use an Indian CIN (e.g. U72200KA2015PTC082345) or CC-XXXXXX (e.g. US-DE5567123)",
  });

// ---- rating (spec V10): integer 1-5 ----
export const ratingSchema = z
  .number({ error: "Please choose a rating" })
  .int({ error: "Rating must be a whole number" })
  .min(1, { error: "Rating must be between 1 and 5" })
  .max(5, { error: "Rating must be between 1 and 5" });

// ---- misc ----
export const fullNameSchema = z
  .string({ error: "Name is required" })
  .trim()
  .min(2, { error: "Name must be at least 2 characters" })
  .max(120, { error: "Name must be at most 120 characters" });

/** Empty string -> undefined; otherwise must be an http(s) URL. */
export const optionalUrlSchema = z
  .string()
  .optional()
  .transform((v) => (v && v.trim() ? v.trim() : undefined))
  .refine((v) => v === undefined || /^https?:\/\/[^\s]+\.[^\s]+$/i.test(v), { error: "Enter a valid URL starting with http(s)://" });

/** Empty string -> undefined. */
export const optionalText = (max: number) =>
  z
    .string()
    .optional()
    .transform((v) => (v && v.trim() ? v.trim() : undefined))
    .refine((v) => v === undefined || v.length <= max, { error: `Must be at most ${max} characters` });

/** For `<input type="number">` registered with RHF: "" -> undefined, else Number. */
export const numberInput = {
  setValueAs: (v: unknown) => (v === "" || v === null || v === undefined ? undefined : Number(v)),
};
