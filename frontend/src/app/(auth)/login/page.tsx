"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, MailWarning, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { AuthHeading } from "@/components/shared/AuthCard";
import { FormField, PasswordInput } from "@/components/shared/FormField";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api/client";
import { useResendVerification } from "@/lib/api/hooks/auth";
import { errorMessage } from "@/lib/forms";
import { roleHome } from "@/lib/nav";
import { loginSchema, type LoginInput } from "@/lib/validation/auth";
import { useAuth } from "@/providers/AuthProvider";

const DEMO = [
  { label: "Student", email: "student@campushire.dev", password: "Student@12345" },
  { label: "Faculty", email: "faculty@campushire.dev", password: "Faculty@12345" },
  { label: "Company", email: "company@campushire.dev", password: "Company@12345" },
  { label: "Admin", email: "admin@campushire.dev", password: "Admin@12345" },
];

/** Only allow same-origin relative redirects. */
function safeNext(next: string | null): string | null {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/login")) return null;
  return next;
}

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { login } = useAuth();
  const resend = useResendVerification();
  const [formError, setFormError] = useState<string | null>(null);
  const [unverified, setUnverified] = useState(false);
  const {
    register,
    handleSubmit,
    setValue,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<LoginInput>({ resolver: zodResolver(loginSchema), defaultValues: { email: "", password: "" } });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    setUnverified(false);
    try {
      const res = await login({ email: values.email, password: values.password });
      router.replace(safeNext(params.get("next")) ?? roleHome(res.user.role));
    } catch (e) {
      if (e instanceof ApiError && e.code === "EMAIL_NOT_VERIFIED") {
        setUnverified(true);
        setFormError("Please verify your email address before signing in.");
      } else if (e instanceof ApiError && e.code === "INVALID_CREDENTIALS") {
        setFormError("Incorrect email or password.");
      } else if (e instanceof ApiError && e.code === "ACCOUNT_DEACTIVATED") {
        setFormError("This account has been deactivated. Contact your administrator.");
      } else {
        setFormError(errorMessage(e, "Could not sign in"));
      }
    }
  });

  return (
    <>
      <AuthHeading title="Welcome back" description="Sign in to your CampusHire account." />
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {formError && (
          <Alert variant="destructive" role="alert">
            <MailWarning />
            <AlertTitle>{unverified ? "Email not verified" : "Sign in failed"}</AlertTitle>
            <AlertDescription>
              {formError}
              {unverified && (
                <Button
                  type="button"
                  variant="link"
                  className="h-auto p-0 pl-1"
                  disabled={resend.isPending}
                  onClick={() =>
                    resend.mutate(getValues("email"), {
                      onSuccess: () => toast.success("Verification email sent. Check your inbox."),
                      onError: (e) => toast.error(errorMessage(e)),
                    })
                  }
                >
                  Resend verification email
                </Button>
              )}
            </AlertDescription>
          </Alert>
        )}
        <FormField label="Email" error={errors.email?.message} required>
          {(p) => <Input {...p} type="email" autoComplete="email" placeholder="you@college.edu" className="h-10 rounded-xl" {...register("email")} />}
        </FormField>
        <FormField label="Password" error={errors.password?.message} required>
          {(p) => <PasswordInput {...p} autoComplete="current-password" placeholder="Your password" {...register("password")} />}
        </FormField>
        <div className="flex justify-end">
          <Link href="/forgot-password" className="text-sm font-medium text-primary hover:underline">
            Forgot password?
          </Link>
        </div>
        <Button type="submit" size="lg" className="h-10 w-full rounded-xl" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="animate-spin" />}
          Sign in
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        New to CampusHire?{" "}
        <Link href="/register" className="font-medium text-primary hover:underline">
          Create a student account
        </Link>{" "}
        or{" "}
        <Link href="/register/company" className="font-medium text-primary hover:underline">
          register your company
        </Link>
        .
      </p>

      <div className="mt-8 rounded-2xl border border-dashed bg-muted/30 p-4">
        <p className="mb-3 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          <Sparkles className="size-3.5" /> Demo accounts
        </p>
        <div className="grid grid-cols-2 gap-2">
          {DEMO.map((d) => (
            <Button
              key={d.label}
              type="button"
              variant="outline"
              size="sm"
              className="rounded-lg"
              onClick={() => {
                setValue("email", d.email, { shouldValidate: true });
                setValue("password", d.password, { shouldValidate: true });
              }}
            >
              {d.label}
            </Button>
          ))}
        </div>
      </div>
    </>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
