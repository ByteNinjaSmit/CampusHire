import {
  Bell,
  BookOpenCheck,
  Briefcase,
  Building2,
  CalendarClock,
  ClipboardCheck,
  Database,
  FileText,
  FolderOpen,
  Gauge,
  Heart,
  LayoutDashboard,
  LifeBuoy,
  MessageSquareText,
  PlusCircle,
  ScrollText,
  Search,
  Settings,
  ShieldCheck,
  Star,
  Users,
  UserCircle,
  BarChart3,
  Activity,
  Inbox,
  FileSignature,
  type LucideIcon,
} from "lucide-react";
import type { Role } from "@/lib/api/types";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  /** Match nested routes as active (default true). Set false for index routes like /student. */
  exact?: boolean;
  keywords?: string[];
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export interface QuickAction {
  label: string;
  href: string;
  icon: LucideIcon;
}

export const roleHome = (role: Role): string => `/${role.toLowerCase()}`;

const shared: NavGroup = {
  label: "Account",
  items: [
    { label: "Notifications", href: "/notifications", icon: Bell },
    { label: "Profile", href: "/profile", icon: UserCircle },
    { label: "Settings", href: "/settings", icon: Settings },
    { label: "Send feedback", href: "/feedback/system", icon: LifeBuoy, keywords: ["bug", "feature", "improvement"] },
  ],
};

const explorer: NavItem = { label: "Explore internships", href: "/internships", icon: Search, exact: false, keywords: ["search", "browse", "jobs"] };
const documents: NavItem = { label: "Documents", href: "/documents", icon: FolderOpen, keywords: ["resume", "pdf", "upload"] };

const NAV: Record<Role, NavGroup[]> = {
  STUDENT: [
    {
      label: "Main",
      items: [
        { label: "Dashboard", href: "/student", icon: LayoutDashboard, exact: true },
        explorer,
        { label: "My applications", href: "/student/applications", icon: Briefcase, exact: false },
        { label: "Saved", href: "/student/saved", icon: Heart },
        { label: "Interviews", href: "/student/interviews", icon: CalendarClock },
        documents,
      ],
    },
    {
      label: "Insights",
      items: [
        { label: "Feedback center", href: "/student/feedback", icon: MessageSquareText },
        { label: "Reports", href: "/student/reports", icon: BarChart3 },
      ],
    },
    shared,
  ],
  FACULTY: [
    {
      label: "Main",
      items: [
        { label: "Dashboard", href: "/faculty", icon: LayoutDashboard, exact: true },
        { label: "My postings", href: "/faculty/internships", icon: Briefcase, exact: false },
        { label: "Interviews", href: "/faculty/interviews", icon: CalendarClock },
        { label: "Evaluations", href: "/faculty/evaluations", icon: ClipboardCheck },
        { label: "Feedback", href: "/faculty/feedback", icon: MessageSquareText },
        { label: "Reports", href: "/faculty/reports", icon: BarChart3 },
      ],
    },
    {
      label: "Browse",
      items: [{ label: "Companies", href: "/faculty/companies", icon: Building2 }, explorer, documents],
    },
    shared,
  ],
  COMPANY: [
    {
      label: "Main",
      items: [
        { label: "Dashboard", href: "/company", icon: LayoutDashboard, exact: true },
        { label: "Internships", href: "/company/internships", icon: Briefcase, exact: false },
        { label: "Interviews", href: "/company/interviews", icon: CalendarClock },
        { label: "Evaluations", href: "/company/evaluations", icon: ClipboardCheck },
        { label: "Feedback", href: "/company/feedback", icon: MessageSquareText },
        { label: "Reports", href: "/company/reports", icon: BarChart3 },
      ],
    },
    {
      label: "Organisation",
      items: [{ label: "Company profile", href: "/company/profile", icon: Building2 }, explorer, documents],
    },
    shared,
  ],
  ADMIN: [
    {
      label: "Control center",
      items: [
        { label: "Overview", href: "/admin", icon: Gauge, exact: true },
        { label: "Users", href: "/admin/users", icon: Users },
        { label: "Companies", href: "/admin/companies", icon: Building2 },
        { label: "Internships", href: "/admin/internships", icon: Briefcase },
        { label: "Applications", href: "/admin/applications", icon: Inbox },
      ],
    },
    {
      label: "Insights",
      items: [
        { label: "Reports", href: "/admin/reports", icon: BarChart3, exact: false },
        { label: "Compliance", href: "/admin/compliance", icon: ShieldCheck },
        { label: "Data import/export", href: "/admin/data", icon: Database },
        { label: "System health", href: "/admin/system", icon: Activity },
        { label: "Audit log", href: "/admin/audit", icon: ScrollText },
        { label: "System feedback", href: "/admin/feedback", icon: Star },
      ],
    },
    {
      label: "Browse",
      items: [explorer, documents],
    },
    shared,
  ],
};

export function navFor(role: Role): NavGroup[] {
  return NAV[role];
}

export function flatNavFor(role: Role): NavItem[] {
  return NAV[role].flatMap((g) => g.items);
}

export const QUICK_ACTIONS: Record<Role, QuickAction[]> = {
  STUDENT: [
    { label: "Browse internships", href: "/internships", icon: Search },
    { label: "Upload a resume", href: "/documents", icon: FileText },
    { label: "Report a problem", href: "/feedback/system", icon: LifeBuoy },
  ],
  FACULTY: [
    { label: "Post an internship", href: "/faculty/internships/new", icon: PlusCircle },
    { label: "Add a company", href: "/faculty/companies", icon: Building2 },
    { label: "Schedule interviews", href: "/faculty/interviews", icon: CalendarClock },
  ],
  COMPANY: [
    { label: "Post an internship", href: "/company/internships/new", icon: PlusCircle },
    { label: "Review candidates", href: "/company/internships", icon: BookOpenCheck },
    { label: "Schedule interviews", href: "/company/interviews", icon: CalendarClock },
  ],
  ADMIN: [
    { label: "Approve internships", href: "/admin/internships", icon: ClipboardCheck },
    { label: "Create a user", href: "/admin/users", icon: Users },
    { label: "Run compliance scan", href: "/admin/compliance", icon: ShieldCheck },
    { label: "Import / export data", href: "/admin/data", icon: FileSignature },
  ],
};

/** Longest-prefix match against a role's nav, used for breadcrumbs/titles. */
export function findNavItem(role: Role, pathname: string): NavItem | undefined {
  const items = flatNavFor(role);
  return items
    .filter((i) => pathname === i.href || (i.exact === false || i.exact === undefined ? pathname.startsWith(i.href + "/") : false))
    .sort((a, b) => b.href.length - a.href.length)[0];
}
