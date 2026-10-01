"use client";

import { useState } from "react";
import { initials } from "@/lib/format";
import { cn } from "@/lib/utils";

const SIZES = {
  sm: "size-8 text-xs rounded-lg",
  md: "size-11 text-sm rounded-xl",
  lg: "size-16 text-lg rounded-2xl",
  xl: "size-24 text-2xl rounded-3xl",
} as const;

/** Company logo with a gradient initials fallback. */
export function CompanyLogo({
  name,
  src,
  size = "md",
  className,
}: {
  name: string;
  src?: string | null;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const base = cn("shrink-0 overflow-hidden border border-border/60 bg-card", SIZES[size], className);
  if (src && !failed) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt={`${name} logo`} className={cn(base, "object-cover")} onError={() => setFailed(true)} />;
  }
  return (
    <div
      aria-label={`${name} logo`}
      className={cn(
        base,
        "flex items-center justify-center bg-gradient-to-br from-indigo-500/15 to-violet-500/15 font-semibold text-indigo-700 dark:text-indigo-300",
      )}
    >
      {initials(name)}
    </div>
  );
}
