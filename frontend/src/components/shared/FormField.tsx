"use client";

import { Eye, EyeOff, X } from "lucide-react";
import { useId, useState, type ComponentProps, type KeyboardEvent, type ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

/**
 * Accessible label + control + hint/error wrapper. Use with RHF:
 *   <FormField label="Email" error={errors.email?.message}><Input {...register("email")} /></FormField>
 * The child receives id / aria-invalid / aria-describedby via the render-prop form.
 */
export function FormField({
  label,
  error,
  hint,
  required,
  className,
  children,
}: {
  label?: string;
  error?: string;
  hint?: string;
  required?: boolean;
  className?: string;
  children: ReactNode | ((p: { id: string; "aria-invalid": boolean; "aria-describedby": string | undefined }) => ReactNode);
}) {
  const id = useId();
  const descId = error || hint ? `${id}-desc` : undefined;
  const props = { id, "aria-invalid": !!error, "aria-describedby": descId };
  return (
    <div className={cn("space-y-1.5", className)}>
      {label && (
        <Label htmlFor={id} className="text-sm font-medium">
          {label}
          {required && <span className="ml-0.5 text-destructive">*</span>}
        </Label>
      )}
      {typeof children === "function" ? children(props) : children}
      {error ? (
        <p id={descId} role="alert" className="text-xs font-medium text-destructive">
          {error}
        </p>
      ) : hint ? (
        <p id={descId} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export function PasswordInput({ className, ...props }: Omit<ComponentProps<typeof Input>, "type">) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <Input {...props} type={show ? "text" : "password"} className={cn("h-10 rounded-xl pr-10", className)} />
      <button
        type="button"
        tabIndex={-1}
        aria-label={show ? "Hide password" : "Show password"}
        onClick={() => setShow((s) => !s)}
        className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-muted-foreground hover:text-foreground"
      >
        {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
      </button>
    </div>
  );
}

/** Chips input (skills, departments). Enter / comma adds, Backspace on empty removes the last. */
export function TagInput({
  value,
  onChange,
  placeholder = "Type and press Enter",
  max = 30,
  className,
  id,
  invalid,
}: {
  value: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
  max?: number;
  className?: string;
  id?: string;
  invalid?: boolean;
}) {
  const [text, setText] = useState("");
  const add = (raw: string) => {
    const t = raw.trim();
    if (!t || value.length >= max) return;
    if (value.some((v) => v.toLowerCase() === t.toLowerCase())) return;
    onChange([...value, t]);
  };
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      add(text);
      setText("");
    } else if (e.key === "Backspace" && !text && value.length) {
      onChange(value.slice(0, -1));
    }
  };
  return (
    <div
      aria-invalid={invalid}
      className={cn(
        "flex min-h-10 flex-wrap items-center gap-1.5 rounded-xl border border-input bg-transparent px-2 py-1.5 focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50 aria-invalid:border-destructive",
        className,
      )}
    >
      {value.map((t) => (
        <Badge key={t} variant="secondary" className="gap-1 rounded-lg pr-1">
          {t}
          <button type="button" aria-label={`Remove ${t}`} onClick={() => onChange(value.filter((v) => v !== t))} className="rounded p-0.5 hover:bg-foreground/10">
            <X className="size-3" />
          </button>
        </Badge>
      ))}
      <input
        id={id}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKey}
        onBlur={() => {
          add(text);
          setText("");
        }}
        placeholder={value.length ? "" : placeholder}
        className="min-w-[8rem] flex-1 bg-transparent px-1 py-0.5 text-sm outline-none placeholder:text-muted-foreground"
      />
    </div>
  );
}
