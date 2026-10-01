"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTheme } from "next-themes";
import { PageHeader } from "@/components/shared/PageHeader";
import { FormField, PasswordInput } from "@/components/shared/FormField";
import { PasswordChecklist } from "@/components/shared/PasswordChecklist";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { useChangePassword } from "@/lib/api/hooks/auth";
import { changePasswordSchema, type ChangePasswordInput } from "@/lib/validation/auth";
import { useAuth } from "@/providers/AuthProvider";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import { Moon, Sun, Laptop, Shield, LogOut } from "lucide-react";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { logout } = useAuth();
  const changePassword = useChangePassword();

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordInput>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });

  const newPasswordValue = watch("new_password");

  const onSubmit = handleSubmit((data) => {
    changePassword.mutate(
      { current_password: data.current_password, new_password: data.new_password },
      {
        onSuccess: () => {
          toast.success("Password changed successfully");
          reset();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to update password")),
      }
    );
  });

  return (
    <div className="space-y-8">
      <PageHeader
        title="Settings"
        description="Configure your appearance preferences and security credentials."
      />

      <div className="grid gap-6 md:grid-cols-2">
        {/* Appearance Settings */}
        <Card className="rounded-2xl border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Appearance</CardTitle>
            <CardDescription>Customize the look and feel of the platform interface.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <RadioGroup
              value={theme}
              onValueChange={setTheme}
              className="grid grid-cols-3 gap-3"
            >
              <div>
                <RadioGroupItem value="light" id="theme-light" className="sr-only" />
                <Label
                  htmlFor="theme-light"
                  className="flex flex-col items-center justify-between rounded-xl border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary cursor-pointer"
                >
                  <Sun className="mb-2 size-6 text-amber-500" />
                  <span className="text-xs font-semibold">Light</span>
                </Label>
              </div>

              <div>
                <RadioGroupItem value="dark" id="theme-dark" className="sr-only" />
                <Label
                  htmlFor="theme-dark"
                  className="flex flex-col items-center justify-between rounded-xl border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary cursor-pointer"
                >
                  <Moon className="mb-2 size-6 text-indigo-400" />
                  <span className="text-xs font-semibold">Dark</span>
                </Label>
              </div>

              <div>
                <RadioGroupItem value="system" id="theme-system" className="sr-only" />
                <Label
                  htmlFor="theme-system"
                  className="flex flex-col items-center justify-between rounded-xl border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary cursor-pointer"
                >
                  <Laptop className="mb-2 size-6 text-muted-foreground" />
                  <span className="text-xs font-semibold">System</span>
                </Label>
              </div>
            </RadioGroup>
          </CardContent>
        </Card>

        {/* Sessions & Logout */}
        <Card className="rounded-2xl border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Session Management</CardTitle>
            <CardDescription>Manage active logins and authenticated devices.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-xl border border-dashed bg-muted/30 p-4">
              <div className="flex items-center gap-3">
                <Shield className="size-5 text-emerald-600 dark:text-emerald-400" />
                <div>
                  <h4 className="text-sm font-semibold">Current Session</h4>
                  <p className="text-xs text-muted-foreground">
                    Connected via browser cookie with rotating refresh tokens.
                  </p>
                </div>
              </div>
            </div>

            <Button
              variant="destructive"
              className="w-full gap-2 rounded-xl"
              onClick={logout}
            >
              <LogOut className="size-4" /> Sign out of current session
            </Button>
          </CardContent>
        </Card>

        {/* Change Password Form */}
        <Card className="rounded-2xl border-border/60 shadow-sm md:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Change Password</CardTitle>
            <CardDescription>
              Ensure your account uses a strong, unique password with mixed characters.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} className="max-w-xl space-y-4">
              <FormField label="Current Password" error={errors.current_password?.message} required>
                {(p) => (
                  <PasswordInput
                    {...p}
                    autoComplete="current-password"
                    placeholder="Enter current password"
                    {...register("current_password")}
                  />
                )}
              </FormField>

              <FormField label="New Password" error={errors.new_password?.message} required>
                {(p) => (
                  <PasswordInput
                    {...p}
                    autoComplete="new-password"
                    placeholder="Create a strong password"
                    {...register("new_password")}
                  />
                )}
              </FormField>

              <PasswordChecklist value={newPasswordValue || ""} />

              <FormField label="Confirm New Password" error={errors.confirm_password?.message} required>
                {(p) => (
                  <PasswordInput
                    {...p}
                    autoComplete="new-password"
                    placeholder="Re-enter new password"
                    {...register("confirm_password")}
                  />
                )}
              </FormField>

              <div className="flex justify-end pt-2">
                <Button type="submit" disabled={isSubmitting} className="rounded-xl">
                  {isSubmitting ? "Updating..." : "Update Password"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
