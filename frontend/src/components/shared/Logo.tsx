import Link from "next/link";
import { GraduationCap } from "lucide-react";
import { cn } from "@/lib/utils";

export function LogoMark({ className }: { className?: string }) {
  return (
    <span className={cn("gradient-brand flex size-9 shrink-0 items-center justify-center rounded-xl text-white shadow-sm", className)}>
      <GraduationCap className="size-5" />
    </span>
  );
}

export function Logo({ href = "/", collapsed, className, light }: { href?: string; collapsed?: boolean; className?: string; light?: boolean }) {
  return (
    <Link href={href} className={cn("inline-flex items-center gap-2.5 font-semibold tracking-tight", className)} aria-label="CampusHire home">
      <LogoMark />
      {!collapsed && <span className={cn("text-lg", light ? "text-white" : "text-foreground")}>CampusHire</span>}
    </Link>
  );
}
