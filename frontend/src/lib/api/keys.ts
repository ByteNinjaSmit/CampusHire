// TanStack Query key factory: qk.<module>.<op>(params). `all` invalidates a whole module.
const k = <T extends readonly unknown[]>(...parts: T) => parts;

export const qk = {
  auth: { all: k("auth"), me: () => k("auth", "me") },
  users: {
    all: k("users"),
    list: (p?: unknown) => k("users", "list", p ?? {}),
    detail: (id: string) => k("users", "detail", id),
  },
  students: {
    all: k("students"),
    list: (p?: unknown) => k("students", "list", p ?? {}),
    me: () => k("students", "me"),
    detail: (id: string) => k("students", "detail", id),
    applications: (id: string, p?: unknown) => k("students", "applications", id, p ?? {}),
  },
  faculty: { all: k("faculty"), list: (p?: unknown) => k("faculty", "list", p ?? {}), me: () => k("faculty", "me") },
  companies: {
    all: k("companies"),
    list: (p?: unknown) => k("companies", "list", p ?? {}),
    detail: (id: string) => k("companies", "detail", id),
    internships: (id: string, p?: unknown) => k("companies", "internships", id, p ?? {}),
    ratings: (id: string) => k("companies", "ratings", id),
    members: (id: string) => k("companies", "members", id),
  },
  internships: {
    all: k("internships"),
    list: (p?: unknown) => k("internships", "list", p ?? {}),
    facets: () => k("internships", "facets"),
    detail: (id: string) => k("internships", "detail", id),
    saved: (p?: unknown) => k("internships", "saved", p ?? {}),
    applications: (id: string, p?: unknown) => k("internships", "applications", id, p ?? {}),
  },
  applications: {
    all: k("applications"),
    list: (p?: unknown) => k("applications", "list", p ?? {}),
    detail: (id: string) => k("applications", "detail", id),
    resumeUrl: (id: string) => k("applications", "resume-url", id),
  },
  interviews: {
    all: k("interviews"),
    list: (p?: unknown) => k("interviews", "list", p ?? {}),
    detail: (id: string) => k("interviews", "detail", id),
  },
  evaluationForms: {
    all: k("evaluation-forms"),
    list: (p?: unknown) => k("evaluation-forms", "list", p ?? {}),
    detail: (id: string) => k("evaluation-forms", "detail", id),
  },
  evaluations: {
    all: k("evaluations"),
    list: (p?: unknown) => k("evaluations", "list", p ?? {}),
    detail: (id: string) => k("evaluations", "detail", id),
  },
  feedback: {
    all: k("feedback"),
    student: (p?: unknown) => k("feedback", "student", p ?? {}),
    studentTrends: (p?: unknown) => k("feedback", "student-trends", p ?? {}),
    company: (p?: unknown) => k("feedback", "company", p ?? {}),
    faculty: (p?: unknown) => k("feedback", "faculty", p ?? {}),
    system: (p?: unknown) => k("feedback", "system", p ?? {}),
    systemSummary: () => k("feedback", "system-summary"),
  },
  documents: {
    all: k("documents"),
    list: (p?: unknown) => k("documents", "list", p ?? {}),
    downloadUrl: (id: string) => k("documents", "download-url", id),
  },
  notifications: {
    all: k("notifications"),
    list: (p?: unknown) => k("notifications", "list", p ?? {}),
    unreadCount: () => k("notifications", "unread-count"),
  },
  reports: {
    all: k("reports"),
    list: () => k("reports", "list"),
    detail: (key: string, p?: unknown) => k("reports", "detail", key, p ?? {}),
  },
  jobs: {
    all: k("jobs"),
    list: (p?: unknown) => k("jobs", "list", p ?? {}),
    detail: (id: string) => k("jobs", "detail", id),
  },
  analytics: { all: k("analytics"), dashboard: () => k("analytics", "dashboard") },
  admin: {
    all: k("admin"),
    health: () => k("admin", "health"),
    metrics: (minutes?: number) => k("admin", "metrics", minutes ?? 60),
    auditLogs: (p?: unknown) => k("admin", "audit-logs", p ?? {}),
    policies: () => k("admin", "policies"),
    violations: (p?: unknown) => k("admin", "violations", p ?? {}),
  },
} as const;
