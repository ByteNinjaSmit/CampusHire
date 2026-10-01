import { BadgeCheck, CalendarCheck2, LineChart, ShieldCheck } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Logo } from "@/components/shared/Logo";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

const POINTS = [
  { icon: BadgeCheck, title: "One profile, every opportunity", text: "Apply to vetted internships with a verified resume and track every step." },
  { icon: CalendarCheck2, title: "Interviews without the back-and-forth", text: "Smart scheduling with notice and deadline rules built in." },
  { icon: LineChart, title: "Placement analytics", text: "Live dashboards for students, faculty, companies and administrators." },
  { icon: ShieldCheck, title: "Secure by design", text: "Role-based access, audited actions and hardened sessions." },
];

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <aside className="gradient-brand relative hidden overflow-hidden p-10 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-24 -top-24 size-80 rounded-full bg-white/10 blur-3xl" aria-hidden />
        <div className="absolute -bottom-32 -left-16 size-96 rounded-full bg-fuchsia-400/20 blur-3xl" aria-hidden />
        <div className="relative">
          <Logo light />
        </div>
        <div className="relative max-w-md space-y-8">
          <div className="space-y-3">
            <h2 className="text-3xl font-semibold leading-tight tracking-tight xl:text-4xl">Launch careers from campus.</h2>
            <p className="text-white/80">The internship and talent platform that connects students, faculty and companies.</p>
          </div>
          <ul className="space-y-5">
            {POINTS.map((p) => (
              <li key={p.title} className="flex gap-3">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-white/15 backdrop-blur">
                  <p.icon className="size-[18px]" />
                </span>
                <div>
                  <p className="text-sm font-semibold">{p.title}</p>
                  <p className="text-sm text-white/75">{p.text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-white/60">&copy; {new Date().getFullYear()} CampusHire</p>
      </aside>

      <main className="flex min-h-screen flex-col">
        <div className="flex items-center justify-between p-4 md:p-6">
          <div className="lg:invisible">
            <Logo />
          </div>
          <div className="flex items-center gap-2">
            <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
              Back to home
            </Link>
            <ThemeToggle />
          </div>
        </div>
        <div className="flex flex-1 items-center justify-center px-4 pb-10 md:px-8">
          <div className="w-full max-w-md">{children}</div>
        </div>
      </main>
    </div>
  );
}
