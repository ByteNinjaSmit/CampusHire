import { NextResponse, type NextRequest } from "next/server";

// Next 16: proxy.ts replaces middleware.ts and always runs on the Node runtime.
// Routing hint only; real authorisation is enforced by the API on every request.
//
// The API sets two cookies on login/refresh:
//   ch_refresh : HttpOnly, Path=/api/v1/auth  (so the browser does NOT send it to this app's routes)
//   ch_role    : readable, Path=/             (this is what we can see here)
// So "logged in" means ch_role is present (ch_refresh is also accepted if it is ever visible).

const ROLE_PREFIX: Record<string, string> = {
  "/student": "STUDENT",
  "/faculty": "FACULTY",
  "/company": "COMPANY",
  "/admin": "ADMIN",
};

const PUBLIC_EXACT = new Set(["/", "/verify-email", "/forgot-password", "/reset-password"]);
const AUTH_ONLY_PUBLIC = ["/login", "/register"]; // logged-in users are bounced to /dashboard
const VALID_ROLES = new Set(["ADMIN", "FACULTY", "STUDENT", "COMPANY"]);

const matches = (path: string, prefix: string) => path === prefix || path.startsWith(prefix + "/");

export default function proxy(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  const roleCookie = req.cookies.get("ch_role")?.value ?? "";
  const hasRole = VALID_ROLES.has(roleCookie);
  const loggedIn = hasRole || !!req.cookies.get("ch_refresh")?.value;

  // Public pages
  if (AUTH_ONLY_PUBLIC.some((p) => matches(pathname, p))) {
    if (loggedIn) return NextResponse.redirect(new URL("/dashboard", req.url));
    return NextResponse.next();
  }
  if (PUBLIC_EXACT.has(pathname)) return NextResponse.next();

  // Everything else is an (app) route and requires a session.
  if (!loggedIn) {
    const url = new URL("/login", req.url);
    url.searchParams.set("next", pathname + search);
    return NextResponse.redirect(url);
  }

  // Role-scoped prefixes
  for (const [prefix, role] of Object.entries(ROLE_PREFIX)) {
    if (matches(pathname, prefix) && hasRole && roleCookie !== role) {
      return NextResponse.redirect(new URL("/dashboard", req.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  // Skip Next internals, static assets and anything with a file extension.
  matcher: ["/((?!api|_next/static|_next/image|favicon.svg|favicon.ico|logo.svg|.*\\..*).*)"],
};
