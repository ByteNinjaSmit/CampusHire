import { z } from "zod";
import {
  emailSchema,
  fullNameSchema,
  gpaSchema,
  optionalPhoneSchema,
  optionalText,
  optionalUrlSchema,
  passwordSchema,
  phoneSchema,
  registrationNumberSchema,
} from "./common";

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, { error: "Password is required" }),
});
export type LoginInput = z.input<typeof loginSchema>;

export const studentRegisterSchema = z
  .object({
    full_name: fullNameSchema,
    email: emailSchema,
    phone: phoneSchema,
    department: z.string().trim().min(2, { error: "Department is required" }).max(80),
    gpa: gpaSchema,
    enrollment_no: optionalText(32),
    graduation_year: z
      .number()
      .int()
      .min(2000, { error: "Enter a year between 2000 and 2100" })
      .max(2100, { error: "Enter a year between 2000 and 2100" })
      .optional(),
    password: passwordSchema,
    confirm_password: z.string().min(1, { error: "Confirm your password" }),
  })
  .refine((v) => v.password === v.confirm_password, { error: "Passwords do not match", path: ["confirm_password"] });
export type StudentRegisterInput = z.input<typeof studentRegisterSchema>;
export type StudentRegisterOutput = z.output<typeof studentRegisterSchema>;

export const companyRegisterSchema = z
  .object({
    full_name: fullNameSchema,
    email: emailSchema,
    phone: optionalPhoneSchema,
    job_title: optionalText(80),
    password: passwordSchema,
    confirm_password: z.string().min(1, { error: "Confirm your password" }),
    company_name: z.string().trim().min(2, { error: "Company name is required" }).max(160),
    registration_number: registrationNumberSchema,
    location: z.string().trim().min(2, { error: "Location is required" }).max(160),
    industry: optionalText(80),
    website: optionalUrlSchema,
    contact_person_name: fullNameSchema,
    contact_email: emailSchema,
    contact_phone: optionalPhoneSchema,
  })
  .refine((v) => v.password === v.confirm_password, { error: "Passwords do not match", path: ["confirm_password"] });
export type CompanyRegisterInput = z.input<typeof companyRegisterSchema>;
export type CompanyRegisterOutput = z.output<typeof companyRegisterSchema>;

export const forgotPasswordSchema = z.object({ email: emailSchema });
export type ForgotPasswordInput = z.input<typeof forgotPasswordSchema>;

export const resetPasswordSchema = z
  .object({ new_password: passwordSchema, confirm_password: z.string().min(1, { error: "Confirm your password" }) })
  .refine((v) => v.new_password === v.confirm_password, { error: "Passwords do not match", path: ["confirm_password"] });
export type ResetPasswordInput = z.input<typeof resetPasswordSchema>;

export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, { error: "Current password is required" }),
    new_password: passwordSchema,
    confirm_password: z.string().min(1, { error: "Confirm your new password" }),
  })
  .refine((v) => v.new_password === v.confirm_password, { error: "Passwords do not match", path: ["confirm_password"] })
  .refine((v) => v.new_password !== v.current_password, { error: "New password must differ from the current one", path: ["new_password"] });
export type ChangePasswordInput = z.input<typeof changePasswordSchema>;
