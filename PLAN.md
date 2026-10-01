# CampusHire — Build Plan

College internship and talent management platform. Source spec: `Assignment_4985_Content_Document_20260923101512960AM.pdf` (3 pages, called "the spec" below).
This plan is the only source of truth for every coding agent. Every decision here is final. If something is not covered, choose the simplest option that matches this plan and write it down in your work-package report.

Legend: **[SPEC]** means the PDF requires it. **[EXT]** is an extension the user asked for on top of the spec. Label extensions in the code and the README.

---

## 0. Ground rules for all agents

1. Stay inside the files your work package (WP) owns (section 7). If you need a change in a file you do not own, add a line to `## Requests` in your final report. Do not edit that file.
2. Use snake_case JSON on the wire, in both directions. Frontend TypeScript types also use snake_case, so nothing gets converted.
3. All IDs are UUID strings. Datetimes are ISO-8601 UTC with `Z`. Plain dates are `YYYY-MM-DD`. Money and GPA are JSON **numbers**, never strings (see 1.3, Decimal gotcha).
4. The API prefix is `/api/v1`. The browser talks to `http://localhost:8000` directly. There is **no reverse proxy, CDN, Caddy or Nginx**.
5. Apply every validation in three layers: Zod (UX), Pydantic/service (authoritative), and Postgres constraints (last line of defence).
6. Do not hide errors or skip tests. Do not use `--no-verify`. Do not use `# type: ignore` or `@ts-ignore` unless a comment explains why.
7. Shell scripts that run inside containers must use LF line endings (see section 9).

---

## 1. Verified-current tech notes (checked 2026-10-01 against the npm and PyPI registries and Docker Hub)

### 1.1 Versions to pin

| Layer | Package | Version / range | Notes |
|---|---|---|---|
| FE | next | `16.3.x` | App Router, Turbopack is the default for dev and build |
| FE | react / react-dom | `19.3.x` | |
| FE | typescript | **`5.9.3`** (pin) | `latest` on npm is TS 7 (the native Go port). Do NOT use it, because Next's TS plugin and typescript-eslint target 5.x |
| FE | tailwindcss / @tailwindcss/postcss | `4.3.x` | CSS-first config (`@theme` in `globals.css`), no `tailwind.config.js` |
| FE | shadcn (CLI) | `4.21.x` | **Must pass `-b radix`**. `-d` defaults to Base UI (`base-nova`), which is wrong for us |
| FE | tw-animate-css | `1.4.x` | replaces `tailwindcss-animate` under TW4 |
| FE | @tanstack/react-query (+devtools) | `5.104.x` | |
| FE | react-hook-form | `7.89.x` | |
| FE | zod | `4.6.x` | Zod 4 API: `z.email()`, `{ error: "..." }` messages |
| FE | @hookform/resolvers | `5.9.x` | supports Zod 4 |
| FE | motion | `13.4.x` | Framer Motion's current package. Import from `"motion/react"` |
| FE | lucide-react | `1.49.x` | |
| FE | echarts | `6.1.x` | wrapped by our own component (no echarts-for-react) |
| FE | cmdk, sonner, next-themes, date-fns | `1.1.x`, `2.0.x`, `0.4.x`, `4.4.x` | |
| FE | eslint / eslint-config-next | **`^9`** / `16.3.x` | `next lint` was removed in Next 16, so run `eslint .` with a flat config |
| FE | @playwright/test | `1.63.x` | |
| BE | python (image) | `3.13-slim` | |
| BE | fastapi | `~=0.142` | |
| BE | uvicorn[standard] | `~=0.54` | |
| BE | pydantic / pydantic-settings | `~=2.13` / `~=2.15` | |
| BE | sqlalchemy[asyncio] | `>=2.0.40,<2.2` | 2.1 is current |
| BE | asyncpg | `~=0.31` | |
| BE | alembic | `~=1.20` | |
| BE | celery[redis] | `~=5.6` | let pip resolve `redis`/`kombu`. Do not pin `redis` separately |
| BE | argon2-cffi | `~=25.1` | `PasswordHasher()` defaults are Argon2id (RFC 9106 profile) |
| BE | pyjwt | `~=2.15` | |
| BE | boto3 | `~=1.43` | used for MinIO (S3 API) |
| BE | email-validator, phonenumbers | `~=2.3`, `~=9.0` | |
| BE | python-multipart | `~=0.0.32` | |
| BE | reportlab | `~=5.0` | **PDF engine = ReportLab only.** WeasyPrint is not used because it needs Pango/Cairo system libraries in the image |
| BE | openpyxl | `~=3.1` | |
| BE | jinja2 | `~=3.1` | email templates |
| BE-dev | pytest, pytest-asyncio, httpx, pytest-cov | `~=9.1`, `~=1.4`, `~=0.28`, latest | |
| Infra | postgres | `postgres:17-alpine` | |
| Infra | redis | `redis:7.4-alpine` | |
| Infra | MinIO | **`pgsty/minio:RELEASE.2026-08-04T00-00-00Z`** | Upstream `minio/minio` images stopped being published in Oct 2025 (community edition is now source-only), and `minio/minio:latest` no longer resolves. `pgsty/minio` is the maintained community fork with the same CLI and env vars. Do not use `minio/mc` either. Buckets are created from Python (boto3) |
| Infra | mailpit | `axllent/mailpit:v1` | SMTP 1025, UI 8025 |
| Infra | node (image) | `node:22-alpine` | Next 16 requires Node >= 20.9 |

### 1.2 Frontend gotchas

- **Next 16:** `middleware.ts` is deprecated and renamed to **`src/proxy.ts`** with `export default function proxy(req)`. It always runs on the Node runtime.
- **Next 16:** `params` and `searchParams` are Promises. Use `await props.params` in server components and `use(props.params)` in client components. `cookies()` and `headers()` are async.
- `NEXT_PUBLIC_*` values are inlined **at build time**, so they must be passed as Docker build args.
- `output: "standalone"` is set in `next.config.ts` so the Docker image stays small.
- **Tailwind 4:** use `@import "tailwindcss";`, `@import "tw-animate-css";`, `@custom-variant dark (&:where(.dark, .dark *));`, and put tokens in `@theme inline { ... }`. PostCSS plugin is `@tailwindcss/postcss`.
- **shadcn:** `npx shadcn@4.21.0 init -t next -b radix --no-monorepo -y` inside the existing app. After init, check `components.json`. Generated components must import from `radix-ui` / `@radix-ui/*`. If they import `@base-ui-components/*`, re-run with `-b radix -f`.
- **Zod 4 + RHF:** `zodResolver(schema)` from `@hookform/resolvers/zod`. Zod 4 dropped `.email()` on strings in favour of `z.email()`.
- **Charts:** use `echarts/core` with tree-shaken chart and component registration inside one client wrapper. Never import `echarts` at module scope in a server component.

### 1.3 Backend gotchas

- **SQLAlchemy async:**
  - Configure `async_sessionmaker(expire_on_commit=False)`.
  - Every relationship gets `lazy="raise"`, so code must use `selectinload` / `joinedload` explicitly. Lazy loads crash under async.
  - Use one session per request through a dependency.
  - Catch `IntegrityError` and map the constraint name to an error code (see 4.2).
- **Pydantic v2 serialises `Decimal` as a string.** Use `Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]` for `gpa`, `stipend_monthly` and similar fields.
- **Postgres generated `tsvector` columns** may only use IMMUTABLE functions. `to_tsvector('english'::regconfig, ...)` with `coalesce` is fine. `array_to_string` is NOT, so skills arrays stay out of the vector.
- **Celery + async:**
  - Tasks are plain sync functions.
  - Each task calls `asyncio.run(coro)`, and `coro` builds its own `create_async_engine(..., poolclass=NullPool)` session through `app/workers/runtime.py`.
  - Never reuse the API's engine or event loop inside a worker.
  - API code enqueues with `celery_app.send_task("<name>", kwargs=...)` (string names, no task imports), wrapped in `anyio.to_thread.run_sync`.
- **MinIO presign inside Docker:**
  - Use two boto3 clients.
  - `s3_internal` uses `endpoint_url=http://minio:9000` for put, head, get and delete from API and workers.
  - `s3_public` uses `endpoint_url=MINIO_PUBLIC_URL=http://localhost:9000` **only to presign**. Presigning runs offline, and the signature covers the Host header, so a presigned URL must use the host the browser will call.
  - Both clients: `Config(signature_version="s3v4", s3={"addressing_style": "path"})`, region `us-east-1`.
  - Uploads use **presigned POST** with conditions `["content-length-range", 1, 5242880]` and `{"Content-Type": "application/pdf"}`. MinIO enforces the 5 MB limit itself.
  - CORS is set with `MINIO_API_CORS_ALLOW_ORIGIN=http://localhost:3000`.
- **argon2-cffi:** keep one module-level `PasswordHasher()`. On login, call `check_needs_rehash` and rehash when needed. `verify` raises `VerifyMismatchError`; catch it and return the generic `INVALID_CREDENTIALS`.
- **pytest-asyncio 1.x:** there is no `event_loop` fixture. Set `asyncio_mode = "auto"` and `asyncio_default_fixture_loop_scope = "session"`, and give session-scoped async fixtures `loop_scope="session"`. The test engine uses `NullPool`.
- **FastAPI:** use `lifespan` (not `on_event`), `Annotated[...]` dependencies, and a custom `RequestValidationError` handler that produces our error envelope.

---

## 2. Final repository tree

```
CampusHire/
├── PLAN.md                          (this file)
├── README.md                        WP1 (WP8 finalises)
├── .gitattributes                   WP1  (* text=auto eol=lf; *.ps1 eol=crlf; *.pdf binary)
├── .gitignore                       WP1
├── .env.example                     WP1
├── docker-compose.yml               WP1
├── scripts/
│   ├── dev.ps1                      WP1  (start Docker Desktop if needed, compose up --build, wait for health)
│   ├── reset.ps1                    WP1  (compose down -v and back up)
│   ├── smoke.ps1                    WP1  (curl health endpoints, login as each seeded role)
│   └── test.ps1                     WP1  (backend pytest in container, then frontend lint/typecheck/build)
├── infra/
│   └── postgres/init/01-test-db.sql WP1  (CREATE DATABASE campushire_test;)
├── backend/
│   ├── Dockerfile                   WP1
│   ├── .dockerignore                WP1
│   ├── docker/entrypoint.sh         WP1  (wait-for deps, alembic upgrade, ensure buckets, seed, exec CMD)
│   ├── pyproject.toml               WP2  (tool config: pytest, ruff, mypy)
│   ├── requirements.txt             WP2
│   ├── requirements-dev.txt         WP2
│   ├── alembic.ini                  WP2
│   ├── alembic/env.py               WP2  (async env)
│   ├── alembic/versions/0001_initial.py  WP2 (entire schema, extensions, seeds compliance_policies)
│   ├── app/
│   │   ├── main.py                  WP2  (create_app, lifespan, CORS, middleware, handlers, include api router, /healthz /readyz)
│   │   ├── api/router.py            WP2  (includes every module router under /api/v1)
│   │   ├── core/
│   │   │   ├── config.py            WP2  (pydantic-settings Settings)
│   │   │   ├── db.py                WP2  (engine, sessionmaker, get_db with side-effect flush)
│   │   │   ├── base.py              WP2  (DeclarativeBase, naming convention, mixins: UUIDPk, Timestamps, SoftArchive)
│   │   │   ├── security.py          WP2  (argon2, JWT, refresh token gen/hash, password policy)
│   │   │   ├── deps.py              WP2  (get_current_user, require_roles, require_verified, pagination params)
│   │   │   ├── permissions.py       WP2  (ownership helpers: can_manage_internship, can_view_application, ...)
│   │   │   ├── errors.py            WP2  (AppError + codes, handlers, IntegrityError→code map)
│   │   │   ├── validators.py        WP2  (email, phone→E.164, password, registration number, PDF magic)
│   │   │   ├── redis.py             WP2  (pool, cache get/set, rate limiter, publish)
│   │   │   ├── ratelimit.py         WP2  (dependency factory rate_limit(key, limit, window))
│   │   │   ├── storage.py           WP2  (s3_internal/s3_public, presign_post, presign_get, head, read_range, delete, ensure_buckets)
│   │   │   ├── celery_app.py        WP2  (Celery() producer instance + config; NO tasks here)
│   │   │   ├── side_effects.py      WP2  (notify(), queue_email(), queue_task(), audit(): staged in session.info, flushed after commit)
│   │   │   ├── middleware.py        WP2  (request id, security headers, metrics → Redis)
│   │   │   ├── pagination.py        WP2  (Page[T] generic, paginate(query))
│   │   │   └── types.py             WP2  (Money/Gpa serializers, enums mirrored from DB)
│   │   ├── models/__init__.py       WP2  (imports every module's models for metadata)
│   │   ├── modules/
│   │   │   ├── auth/        router.py service.py repository.py models.py schemas.py   WP2 (all)
│   │   │   ├── users/       router.py service.py repository.py models.py schemas.py   WP2 (all)
│   │   │   ├── students/    models.py=WP2 | router.py service.py repository.py schemas.py = WP3
│   │   │   ├── faculty/     models.py=WP2 | rest = WP3
│   │   │   ├── companies/   models.py=WP2 | rest = WP3
│   │   │   ├── internships/ models.py=WP2 | rest = WP3
│   │   │   ├── applications/models.py=WP2 | rest = WP3 (+ state_machine.py WP3)
│   │   │   ├── interviews/  models.py=WP2 | rest = WP3
│   │   │   ├── evaluations/ models.py=WP2 | rest = WP3
│   │   │   ├── feedback/    models.py=WP2 | rest = WP3
│   │   │   ├── documents/   models.py=WP2 | rest = WP3   [EXT documents center]
│   │   │   ├── notifications/ models.py=WP2 | router.py service.py repository.py schemas.py ws.py = WP4
│   │   │   ├── reports/     router.py service.py schemas.py builders/*.py renderers/{pdf,xlsx}.py = WP4 (models: jobs table lives in admin/models.py)
│   │   │   ├── analytics/   router.py service.py schemas.py = WP4
│   │   │   └── admin/       models.py=WP2 (jobs, audit_logs, login_events, compliance_*) | router.py service.py repository.py schemas.py importer.py exporter.py health.py = WP4
│   │   ├── workers/                  WP4
│   │   │   ├── main.py              (imports core.celery_app, registers tasks, beat_schedule)
│   │   │   ├── runtime.py           (run_async helper with NullPool engine)
│   │   │   ├── tasks/{emails,reports,data,maintenance,interviews}.py
│   │   │   └── templates/emails/*.html (+ .txt)
│   │   └── seed/                     WP2
│   │       ├── __main__.py          (python -m app.seed; idempotent)
│   │       ├── data.py              (users, companies, internships, …)
│   │       └── resume_pdf.py        (ReportLab sample resume generator)
│   └── tests/
│       ├── conftest.py               WP2
│       ├── factories.py              WP2
│       ├── test_auth.py, test_users.py, test_validators.py                 WP2
│       ├── test_students.py, test_companies.py, test_internships.py,
│       │   test_applications.py, test_application_race.py, test_interviews.py,
│       │   test_evaluations.py, test_feedback.py, test_documents.py        WP3
│       ├── test_notifications.py, test_reports.py, test_analytics.py,
│       │   test_admin.py, test_workers.py                                  WP4
│       └── test_rbac_matrix.py, test_spec_compliance.py                    WP8
└── frontend/
    ├── Dockerfile                    WP1
    ├── .dockerignore                 WP1
    ├── package.json, package-lock.json, next.config.ts, tsconfig.json, postcss.config.mjs,
    │   eslint.config.mjs, components.json, playwright.config.ts           WP5
    ├── public/ (logo.svg, favicon)   WP5
    ├── e2e/*.spec.ts                 WP8
    └── src/
        ├── proxy.ts                  WP5  (route guard by cookies ch_refresh + ch_role)
        ├── app/
        │   ├── layout.tsx, globals.css, page.tsx (landing), not-found.tsx, error.tsx   WP5
        │   ├── (auth)/login, register, register/company, verify-email, forgot-password, reset-password   WP5
        │   └── (app)/
        │       ├── layout.tsx (AppShell)                 WP5
        │       ├── dashboard/page.tsx (redirect /{role}) WP5
        │       ├── notifications/, profile/, settings/, feedback/system/   WP5
        │       ├── internships/ (explorer, [id], [id]/apply)                WP6
        │       ├── documents/                                              WP6
        │       ├── student/**                                              WP6
        │       ├── faculty/**, company/**, admin/**, companies/**          WP7
        ├── components/
        │   ├── ui/**        (shadcn generated)                             WP5
        │   ├── layout/**    (AppShell, Sidebar, Topbar, CommandPalette, ThemeToggle, NotificationBell, UserMenu)  WP5
        │   └── shared/**    (see 5.3)                                      WP5
        ├── features/
        │   ├── student/**, internships/**, applications-wizard/**, documents/**   WP6
        │   └── faculty/**, company/**, admin/**, review/**, evaluations/**, reports/**, companies/**  WP7
        ├── lib/
        │   ├── api/client.ts, api/types.ts, api/endpoints/*.ts, api/hooks/*.ts, api/ws.ts   WP5
        │   ├── validation/*.ts (Zod mirrors of section 3 rules)            WP5
        │   ├── auth/*.ts (token store, session context)                   WP5
        │   ├── nav.ts (sidebar config for all roles)                      WP5
        │   ├── format.ts, status.ts (labels/colors), utils.ts (cn)        WP5
        └── providers/ (QueryProvider, ThemeProvider, AuthProvider, RealtimeProvider)   WP5
```

---

## 3. Database schema (PostgreSQL 17)

Migration `0001_initial.py` (WP2) creates everything below.

### 3.1 Conventions

- Extensions: `CREATE EXTENSION IF NOT EXISTS citext; pg_trgm; btree_gin;`. `gen_random_uuid()` is built in.
- Every table has `id uuid PK DEFAULT gen_random_uuid()`, except where marked otherwise.
- Every table has `created_at timestamptz NOT NULL DEFAULT now()` and `updated_at timestamptz NOT NULL DEFAULT now()`. `updated_at` is set by SQLAlchemy `onupdate`.
- Enums are `varchar` plus a named CHECK, not PG enum types (easier migrations). Constraint naming follows the `MetaData` naming convention: `ck_<table>_<name>`, `uq_<table>_<cols>`, `fk_...`, `ix_...`.
- Soft archive is `archived_at timestamptz NULL`. Active rows are those with `archived_at IS NULL`.

### 3.2 Identity and auth

**users**

| col | type | constraints |
|---|---|---|
| email | citext | NOT NULL, UNIQUE `uq_users_email`, CHECK `email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$'` (coarse; RFC 5322 is enforced in the app with email-validator) |
| password_hash | text | NOT NULL |
| role | varchar(16) | NOT NULL CHECK `role IN ('ADMIN','FACULTY','STUDENT','COMPANY')` |
| full_name | varchar(120) | NOT NULL CHECK `length(trim(full_name)) >= 2` |
| phone | varchar(16) | NULL, CHECK `phone ~ '^\+?[1-9][0-9]{9,14}$'` (10–15 digits, stored E.164) |
| avatar_url | text | NULL |
| is_active | boolean | NOT NULL DEFAULT true |
| email_verified_at | timestamptz | NULL |
| last_login_at | timestamptz | NULL |
| deactivated_at | timestamptz | NULL |
| deactivated_reason | text | NULL |

Indexes: `ix_users_role`, GIN trigram `ix_users_full_name_trgm (full_name gin_trgm_ops)`.

**refresh_tokens**

`id uuid`, `user_id FK users ON DELETE CASCADE`, `family_id uuid NOT NULL`, `token_hash char(64) UNIQUE` (sha256 hex), `expires_at timestamptz NOT NULL`, `revoked_at`, `replaced_by_id uuid NULL`, `user_agent text`, `ip inet`.
Indexes: `(user_id)`, `(family_id)`.

**user_tokens** (email verification and password reset)

`user_id FK CASCADE`, `purpose varchar(16) CHECK IN ('VERIFY_EMAIL','RESET_PASSWORD')`, `token_hash char(64) UNIQUE`, `expires_at`, `used_at`.

**login_events**

`id bigserial PK`, `user_id FK NULL`, `email citext`, `success bool`, `ip inet`, `user_agent text`, `created_at`.
Index `(created_at)` (feeds "login trends").

### 3.3 Profiles

**students**

| col | type | constraints |
|---|---|---|
| user_id | uuid | PK, FK users ON DELETE CASCADE |
| enrollment_no | varchar(32) | UNIQUE NULL |
| department | varchar(80) | NOT NULL |
| gpa | numeric(3,2) | NOT NULL CHECK `gpa >= 0.0 AND gpa <= 4.0` |
| graduation_year | smallint | NULL CHECK 2000..2100 |
| skills | text[] | NOT NULL DEFAULT '{}' |
| bio | text | NULL CHECK length <= 2000 |
| linkedin_url, github_url, portfolio_url | text | NULL |
| default_resume_id | uuid | FK documents NULL ON DELETE SET NULL |

Indexes: `(department)`, `(gpa)`.

**faculty**

`user_id PK FK`, `employee_id varchar(32) UNIQUE NULL`, `department varchar(80) NOT NULL`, `designation varchar(80)`.

**company_members** [EXT COMPANY role]

`user_id PK FK users`, `company_id FK companies ON DELETE CASCADE`, `job_title varchar(80)`.

### 3.4 Companies

**companies**

| col | type | constraints |
|---|---|---|
| name | varchar(160) | NOT NULL |
| registration_number | varchar(32) | NOT NULL, UNIQUE `uq_companies_registration_number`, CHECK `registration_number ~ '^([LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}\|[A-Z]{2}-[A-Z0-9]{6,15})$'` |
| industry | varchar(80) | NULL |
| location | varchar(160) | NOT NULL (city, state/country display string) |
| website | text | NULL |
| description | text | NULL |
| logo_document_id | uuid | FK documents NULL |
| contact_person_name | varchar(120) | NOT NULL |
| contact_email | citext | NOT NULL |
| contact_phone | varchar(16) | NULL CHECK same as users.phone |
| status | varchar(16) | NOT NULL DEFAULT 'ACTIVE' CHECK IN ('PENDING','ACTIVE','ARCHIVED') |
| archived_at | timestamptz | NULL |
| created_by | uuid | FK users NULL |

The registration number is **valid** if it matches one of two formats:
- Indian CIN (21 chars, e.g. `U72200KA2015PTC082345`)
- International format `CC-XXXXXX` (ISO country code, hyphen, 6–15 alphanumerics, e.g. `US-DE5567123`)

It is normalised to upper case with spaces stripped before validation.

Indexes: GIN trigram on `name`, `(status)`.

### 3.5 Internships

**internships**

| col | type | constraints |
|---|---|---|
| company_id | uuid | FK companies NOT NULL ON DELETE RESTRICT |
| posted_by | uuid | FK users NOT NULL (FACULTY, COMPANY, or ADMIN) |
| title | varchar(160) | NOT NULL CHECK length >= 3 |
| description | text | NOT NULL CHECK length >= 20 |
| domain | varchar(60) | NOT NULL (from fixed list: Software Engineering, Data Science, AI/ML, Cloud & DevOps, Cybersecurity, Product Design, Product Management, Marketing, Finance, Operations, Hardware/Embedded, Research) |
| location | varchar(160) | NOT NULL |
| work_mode | varchar(10) | NOT NULL CHECK IN ('ONSITE','REMOTE','HYBRID') |
| stipend_monthly | numeric(10,2) | NOT NULL DEFAULT 0 CHECK >= 0 |
| currency | char(3) | NOT NULL DEFAULT 'INR' |
| duration_weeks | smallint | NOT NULL CHECK `duration_weeks BETWEEN 4 AND 26` |
| start_date | date | NOT NULL |
| end_date | date | NOT NULL |
| application_deadline | timestamptz | NOT NULL |
| openings | smallint | NOT NULL DEFAULT 1 CHECK > 0 |
| skills | text[] | NOT NULL DEFAULT '{}' |
| min_gpa | numeric(3,2) | NULL CHECK 0..4 |
| eligible_departments | text[] | NOT NULL DEFAULT '{}' (empty = all) |
| status | varchar(20) | NOT NULL DEFAULT 'DRAFT' CHECK IN ('DRAFT','PENDING_APPROVAL','APPROVED','REJECTED','CLOSED') |
| rejection_reason | text | NULL |
| approved_by | uuid FK users | NULL |
| approved_at | timestamptz | NULL |
| archived_at | timestamptz | NULL |
| search_vector | tsvector | GENERATED ALWAYS AS (setweight(to_tsvector('english', coalesce(title,'')),'A') \|\| setweight(to_tsvector('english', coalesce(domain,'')),'B') \|\| setweight(to_tsvector('english', coalesce(location,'')),'C') \|\| setweight(to_tsvector('english', coalesce(description,'')),'D')) STORED |

Table CHECKs:
- `ck_internships_dates`: `start_date < end_date`
- `ck_internships_duration_days`: `(end_date - start_date) BETWEEN 28 AND 183` (4 weeks to 6 months)
- `ck_internships_deadline_before_start`: `application_deadline < start_date::timestamptz`

Service rules (cannot be DB CHECKs, because they depend on `now()`):
- On create, and on update whenever dates change: `start_date > today`, `end_date > today`, `application_deadline > now()`.
- `duration_weeks` must equal `round((end_date - start_date)/7)` ± 1. The API computes it when it is omitted.

Indexes:
- GIN `search_vector`
- GIN trigram `title`
- `(company_id)`, `(posted_by)`, `(domain)`, `(stipend_monthly)`, `(status, application_deadline)`
- Partial `ix_internships_open ON (application_deadline) WHERE status='APPROVED' AND archived_at IS NULL`

**saved_internships** [EXT]

`student_id FK students.user_id CASCADE`, `internship_id FK CASCADE`, `created_at`. PK `(student_id, internship_id)`.

### 3.6 Documents [EXT documents center, also backs the spec's resume rule]

**documents**

| col | type | constraints |
|---|---|---|
| owner_id | uuid | FK users NOT NULL |
| kind | varchar(20) | CHECK IN ('RESUME','COVER_LETTER','TRANSCRIPT','OFFER_LETTER','LOGO','REPORT','EXPORT','IMPORT','OTHER') |
| bucket | varchar(32) | NOT NULL CHECK IN ('resumes','documents','reports') |
| object_key | text | NOT NULL UNIQUE |
| filename | varchar(255) | NOT NULL |
| content_type | varchar(100) | NOT NULL |
| size_bytes | bigint | NOT NULL CHECK > 0 |
| status | varchar(16) | NOT NULL DEFAULT 'PENDING_UPLOAD' CHECK IN ('PENDING_UPLOAD','UPLOADED','REJECTED') |
| verification_status | varchar(16) | NOT NULL DEFAULT 'PENDING' CHECK IN ('PENDING','VERIFIED','REJECTED') |
| verified_by | uuid FK users | NULL |
| verified_at | timestamptz | NULL |
| verification_note | text | NULL |
| deleted_at | timestamptz | NULL |

CHECK `ck_documents_resume_pdf`: `kind <> 'RESUME' OR (content_type = 'application/pdf' AND size_bytes <= 5242880)`.
Index `(owner_id, kind)`.

Object key format: `{bucket}/{owner_id}/{document_id}/{slugified-filename}` (stored without the bucket prefix).

### 3.7 Applications

**applications**

| col | type | constraints |
|---|---|---|
| internship_id | uuid | FK internships NOT NULL ON DELETE RESTRICT |
| student_id | uuid | FK students.user_id NOT NULL |
| resume_document_id | uuid | FK documents **NOT NULL** (spec: resume mandatory) |
| cover_letter | text | NOT NULL CHECK `length(cover_letter) BETWEEN 50 AND 5000` |
| qualifications | text | NOT NULL CHECK `length(qualifications) BETWEEN 10 AND 3000` |
| answers | jsonb | NOT NULL DEFAULT '{}' (wizard extras: skills[], coursework, availability_from, portfolio_url) |
| status | varchar(16) | NOT NULL DEFAULT 'PENDING' CHECK `ck_applications_status` IN ('PENDING','UNDER_REVIEW','SHORTLISTED','INTERVIEW','ACCEPTED','REJECTED','WITHDRAWN') |
| status_changed_at | timestamptz | NOT NULL DEFAULT now() |
| decision_note | text | NULL |
| offer_details | jsonb | NULL (`{stipend_monthly, start_date, joining_location, notes}` set when ACCEPTED) |
| withdrawn_reason | text | NULL |
| completed_at | timestamptz | NULL (internship completed; unlocks post-internship feedback) |

- **`uq_applications_student_internship UNIQUE (student_id, internship_id)`**. This enforces the spec's duplicate-prevention rule. A withdrawn application still blocks reapplying.
- Indexes: `(internship_id, status)`, `(student_id, status)`, `(status_changed_at)`.
- Spec mapping: the spec lists `pending, shortlisted, rejected, accepted, withdrawn`. `UNDER_REVIEW` and `INTERVIEW` are **[EXT]**. In the UI they are labelled as sub-states of "pending" and "shortlisted" respectively.

**application_status_history**

`id bigserial`, `application_id FK CASCADE`, `from_status varchar(16) NULL`, `to_status varchar(16) NOT NULL`, `changed_by uuid FK users NULL`, `note text`, `created_at`.
Index `(application_id, created_at)`.

### 3.8 Application state machine (`app/modules/applications/state_machine.py`, WP3)

```
                ┌──────────────┐
  submit ──────▶│   PENDING    │──────────────┐
                └──┬───────┬───┘              │
         review    │       │ shortlist        │ reject
                   ▼       │                  │
           ┌──────────────┐│                  │
           │ UNDER_REVIEW ││──── reject ──────▶│
           └──────┬───────┘│                  ▼
         shortlist│        ▼           ┌────────────┐
                  └──▶┌─────────────┐  │  REJECTED  │ (terminal)
                      │ SHORTLISTED │─▶└────────────┘
                      └──┬───────┬──┘        ▲
     schedule interview  │       │ accept    │ reject
     (auto)              ▼       ▼           │
                  ┌───────────┐ ┌──────────┐ │
                  │ INTERVIEW │▶│ ACCEPTED │ │
                  └─────┬─────┘ └────┬─────┘ │
                        └─ reject ───┼───────┘
   any non-terminal ── student withdraw ──▶ WITHDRAWN (terminal)
```

Allowed transitions (`TRANSITIONS: dict[str, set[str]]`):

| from | to (staff: FACULTY owner / COMPANY owner / ADMIN) | to (STUDENT owner) |
|---|---|---|
| PENDING | UNDER_REVIEW, SHORTLISTED, REJECTED | WITHDRAWN |
| UNDER_REVIEW | SHORTLISTED, REJECTED | WITHDRAWN |
| SHORTLISTED | INTERVIEW (system only, via interview create), ACCEPTED, REJECTED | WITHDRAWN |
| INTERVIEW | ACCEPTED, REJECTED, SHORTLISTED (system only, when the last active interview is cancelled) | WITHDRAWN |
| ACCEPTED | — (completion is a separate flag `completed_at`) | WITHDRAWN (declines offer) |
| REJECTED | — | — |
| WITHDRAWN | — | — |

Every transition:
1. Locks the row with `SELECT ... FOR UPDATE`.
2. Checks the transition table. Any other move raises 409 `INVALID_STATUS_TRANSITION`.
3. Writes `application_status_history`.
4. Sets `status_changed_at`.
5. Calls `notify()` for the student, and for internship owners when the student withdraws.
6. Queues a status email.
7. Writes an audit row.

Moving to `ACCEPTED` requires `offer_details`. An `ACCEPTED` application gets `completed_at` set through `POST /applications/{id}/complete`, which is allowed only when `today >= internship.end_date`, or by ADMIN at any time.

### 3.9 Interviews

**interviews**

| col | type | constraints |
|---|---|---|
| application_id | uuid | FK applications CASCADE NOT NULL |
| scheduled_by | uuid | FK users NOT NULL |
| scheduled_at | timestamptz | NOT NULL |
| duration_minutes | smallint | NOT NULL DEFAULT 30 CHECK BETWEEN 15 AND 240 |
| mode | varchar(10) | NOT NULL CHECK IN ('ONLINE','ONSITE','PHONE') |
| location | text | NULL (ONSITE) |
| meeting_link | text | NULL (ONLINE) |
| interviewer_name | varchar(120) | NOT NULL |
| interviewer_email | citext | NULL |
| interviewer_user_id | uuid FK users | NULL |
| status | varchar(12) | NOT NULL DEFAULT 'SCHEDULED' CHECK IN ('SCHEDULED','RESCHEDULED','COMPLETED','CANCELLED','NO_SHOW') |
| result | varchar(10) | NOT NULL DEFAULT 'PENDING' CHECK IN ('PENDING','PASS','FAIL','ON_HOLD') |
| score | smallint | NULL CHECK BETWEEN 1 AND 5 |
| comments | text | NULL (internal) |
| feedback_for_student | text | NULL (visible to the student once COMPLETED) |
| cancel_reason | text | NULL |
| reschedule_count | smallint | NOT NULL DEFAULT 0 |
| reminder_sent_at | timestamptz | NULL |

Indexes: `(application_id)`, `(scheduled_at)`, `(interviewer_user_id, scheduled_at)`.

Service rules, on create and reschedule:
- **R1 notice:** `scheduled_at >= now() + 24h`. Otherwise 422 `INTERVIEW_NOTICE_TOO_SHORT`.
- **R2 deadline** (spec: "cannot schedule past deadline"): `scheduled_at + duration <= internship.application_deadline`. Otherwise 422 `INTERVIEW_AFTER_DEADLINE`. The README must state this as our reading of the spec.
- **R3:** the application status must be one of SHORTLISTED, INTERVIEW. Otherwise 409 `INVALID_STATUS_TRANSITION`.
- **R4:** no overlap with another SCHEDULED/RESCHEDULED interview of the same student. Otherwise 409 `INTERVIEW_CONFLICT`.
- **R5:** mode ONLINE requires `meeting_link`. Mode ONSITE requires `location`.
- Creating an interview moves the application SHORTLISTED → INTERVIEW.
- Reschedule sets status `RESCHEDULED` and increments `reschedule_count`.
- Cancel sets `CANCELLED` and `cancel_reason`. If no active interview remains, the application goes INTERVIEW → SHORTLISTED.
- Result update is allowed only when `scheduled_at <= now()` (ADMIN may bypass). It sets status COMPLETED or NO_SHOW.

### 3.10 Evaluations

**evaluation_forms**

`name varchar(120) NOT NULL`, `description text`, `created_by FK users`, `is_default bool DEFAULT false`, `archived_at`.

**evaluation_criteria**

`form_id FK CASCADE`, `name varchar(120) NOT NULL`, `description text`, `weight numeric(4,2) NOT NULL DEFAULT 1 CHECK > 0 AND <= 10`, `max_score smallint NOT NULL DEFAULT 5 CHECK IN (5,10)`, `position smallint NOT NULL`.
UNIQUE `(form_id, position)`.

**evaluations**

`form_id FK`, `application_id FK applications CASCADE`, `evaluator_id FK users`, `overall_comments text`, `recommendation varchar(16) CHECK IN ('STRONG_YES','YES','MAYBE','NO')`, `weighted_score numeric(5,2) NOT NULL` (0–100, computed by the service), `shared_with_student bool NOT NULL DEFAULT false`, `archived_at`.
UNIQUE `(application_id, evaluator_id, form_id)`.

**evaluation_scores**

`evaluation_id FK CASCADE`, `criterion_id FK`, `score smallint NOT NULL CHECK BETWEEN 0 AND 10`, `comment text`.
PK `(evaluation_id, criterion_id)`. The service also checks `score <= criterion.max_score`.

The migration seeds a default form "Standard Internship Evaluation" with 5 criteria (Technical Skills, Problem Solving, Communication, Culture Fit, Initiative), each `max_score 5`.

### 3.11 Feedback (spec section 5)

**student_feedback** (post-internship; student rates company/internship)

`application_id FK UNIQUE NOT NULL`, `student_id FK`, `company_id FK` (denormalised), `internship_id FK` (denormalised), `company_culture smallint`, `mentorship smallint`, `technical_learning smallint`, `work_environment smallint`, `overall smallint`. Each rating is `NOT NULL CHECK BETWEEN 1 AND 5`. Also `comments text`, `suggestions text`, `is_anonymous bool DEFAULT false`, `response_body text NULL`, `responded_by FK users NULL`, `responded_at NULL`.
Indexes: `(company_id, created_at)`, `(internship_id)`.

Allowed only when the application is `ACCEPTED` and (`completed_at IS NOT NULL` or `internship.end_date <= today`).

**company_feedback** (company/staff rates student)

`application_id FK NOT NULL`, `author_id FK users`, `technical_skills`, `soft_skills`, `punctuality`, `responsibility`, `teamwork`, `learning_ability` (each smallint 1–5 CHECK), `strengths text`, `improvements text`, `hire_likelihood smallint NOT NULL CHECK 1..5` (1 = very unlikely … 5 = definitely, "likelihood to hire full-time").
UNIQUE `(application_id, author_id)`.

**faculty_feedback**

`internship_id FK NOT NULL`, `application_id FK NULL`, `faculty_id FK users`, `course_suitability`, `learning_outcomes`, `internship_quality` (each smallint 1–5 CHECK), `suggestions text`, `comments text`.
Index `(internship_id)`.

**system_feedback**

`user_id FK`, `type varchar(12) CHECK IN ('FEATURE','BUG','IMPROVEMENT')`, `title varchar(160) NOT NULL`, `description text NOT NULL`, `page_url text`, `severity varchar(8) CHECK IN ('LOW','MEDIUM','HIGH','CRITICAL') NULL` (bugs), `status varchar(12) NOT NULL DEFAULT 'NEW' CHECK IN ('NEW','TRIAGED','PLANNED','IN_PROGRESS','DONE','WONT_DO')`, `priority varchar(8) CHECK IN ('LOW','MEDIUM','HIGH') NULL`, `admin_notes text`.

**feedback_action_items**

`system_feedback_id FK CASCADE`, `title varchar(160)`, `assignee_id FK users NULL`, `status varchar(12) CHECK IN ('OPEN','IN_PROGRESS','DONE') DEFAULT 'OPEN'`, `due_date date NULL`.

### 3.12 Notifications, audit, jobs, compliance

**notifications**

`user_id FK CASCADE`, `type varchar(40)` (e.g. `APPLICATION_STATUS`, `INTERVIEW_SCHEDULED`, `INTERNSHIP_APPROVED`, `SYSTEM`), `title varchar(160)`, `body text`, `link text`, `data jsonb DEFAULT '{}'`, `read_at`.
Index `(user_id, read_at, created_at DESC)`.

**audit_logs**

`id bigserial`, `actor_id FK NULL`, `action varchar(60)` (e.g. `internship.approve`), `entity_type varchar(40)`, `entity_id uuid NULL`, `before jsonb`, `after jsonb`, `ip inet`, `user_agent text`, `created_at`.
Indexes: `(entity_type, entity_id)`, `(actor_id)`, `(created_at)`.

**jobs** (async exports, imports, reports)

`type varchar(20) CHECK IN ('REPORT_EXPORT','DATA_EXPORT','DATA_IMPORT','COMPLIANCE_SCAN')`, `status varchar(12) CHECK IN ('QUEUED','RUNNING','SUCCEEDED','FAILED')`, `requested_by FK`, `params jsonb`, `progress smallint DEFAULT 0 CHECK 0..100`, `result jsonb` (e.g. `{rows_ok, rows_failed, errors:[{row,field,message}]}`), `result_document_id FK documents NULL`, `error text`, `started_at`, `finished_at`.

**compliance_policies**

`code varchar(40) UNIQUE`, `name`, `description`, `is_active bool`, `severity varchar(8)`.
Seeded rows:
- `RESUME_UNVERIFIED_7D`: a resume attached to an active application has been PENDING verification for more than 7 days.
- `INTERNSHIP_PAST_DEADLINE_OPEN`: an approved internship's deadline passed but it was not closed.
- `INTERVIEW_SHORT_NOTICE`: should never fire; detects data that bypassed the rule.
- `UNPAID_LONG_INTERNSHIP`: stipend 0 and duration > 12 weeks.
- `INACTIVE_COMPANY_POSTING`: an internship belongs to an ARCHIVED or PENDING company.

**policy_violations**

`policy_id FK`, `entity_type`, `entity_id uuid`, `details jsonb`, `status varchar(10) CHECK IN ('OPEN','RESOLVED','DISMISSED') DEFAULT 'OPEN'`, `resolved_by FK NULL`, `resolved_at`, `note text`.
UNIQUE `(policy_id, entity_type, entity_id)`, so scans are idempotent.

### 3.13 Search query (internships list)

When `q` is present:

```sql
WHERE (search_vector @@ websearch_to_tsquery('english', :q) OR title % :q OR c.name % :q)
ORDER BY ts_rank(search_vector, websearch_to_tsquery('english', :q)) DESC,
         similarity(title, :q) DESC
```

Run `SET pg_trgm.similarity_threshold = 0.25` per session (transaction-local).

---

## 4. REST API (prefix `/api/v1`)

### 4.1 Conventions

- Auth header: `Authorization: Bearer <access_jwt>`. The access JWT is HS256 and lives 15 min. Claims: `sub`, `role`, `jti`, `type:"access"`, `iat`, `exp`.
- Refresh token:
  - Opaque, 32 random bytes, url-safe.
  - Stored as a sha256 hash.
  - Cookie: `ch_refresh`, `HttpOnly; SameSite=Lax; Path=/api/v1/auth; Max-Age=7d; Secure=<COOKIE_SECURE>`.
  - Rotated on every `/auth/refresh`, which revokes the old token and links `replaced_by_id`.
  - **Reuse detection:** if a revoked token is presented, revoke the whole `family_id` and return 401 `TOKEN_REUSED`.
- Cookie `ch_role` (NOT HttpOnly, `Path=/`, same lifetime) holds just the role string. `proxy.ts` uses it for routing only. Real authorisation is always enforced by the API.
  - Both cookies are host-only on `localhost`. Cookies ignore ports, so Next on :3000 sees them.
  - `/auth/refresh` and `/auth/logout` require header `X-Requested-With: campushire` plus an Origin check against `CORS_ORIGINS` (CSRF guard).
- CORS: `allow_origins=[http://localhost:3000]`, `allow_credentials=True`, `expose_headers=["X-Request-ID"]`.
- Pagination: query `page` (1-based, default 1), `page_size` (default 20, max 100). Response is `Page<T>` (see section 6).
- Errors always use the envelope `{"error": {"code": "...", "message": "...", "details": [{"field": "email", "message": "..."}], "request_id": "..."}}`.

### 4.2 Error codes

| HTTP | code | trigger |
|---|---|---|
| 400 | BAD_REQUEST | malformed input not caught by schema |
| 401 | UNAUTHENTICATED / TOKEN_EXPIRED / TOKEN_INVALID / TOKEN_REUSED / INVALID_CREDENTIALS | |
| 403 | FORBIDDEN / EMAIL_NOT_VERIFIED / ACCOUNT_DEACTIVATED | |
| 404 | NOT_FOUND | also returned instead of 403 when the resource is outside the caller's scope (prevents ID enumeration) |
| 409 | DUPLICATE_EMAIL (`uq_users_email`), DUPLICATE_APPLICATION (`uq_applications_student_internship`), DUPLICATE_REGISTRATION_NUMBER (`uq_companies_registration_number`), DUPLICATE_FEEDBACK, DUPLICATE_EVALUATION, INVALID_STATUS_TRANSITION, INTERNSHIP_NOT_OPEN, DEADLINE_PASSED, INTERVIEW_CONFLICT, IN_USE (hard delete blocked), CONFLICT | |
| 422 | VALIDATION_ERROR, INTERVIEW_NOTICE_TOO_SHORT, INTERVIEW_AFTER_DEADLINE, RESUME_REQUIRED, RESUME_INVALID, FILE_TOO_LARGE, INELIGIBLE (GPA/department) | |
| 429 | RATE_LIMITED (headers `Retry-After`) | |
| 500 | INTERNAL_ERROR | |

### 4.3 Rate limits (Redis fixed window)

| Endpoint | Limit |
|---|---|
| login | 5/min per (ip, email) |
| register | 10/h per ip |
| forgot/resend | 3/h per email |
| upload-url | 30/min per user |
| everything else | 300/min per user or ip |

### 4.4 Endpoints and permissions

Role columns: A = ADMIN, F = FACULTY, S = STUDENT, C = COMPANY [EXT]. "own" means scoped by ownership:
- **Internship owner:** `posted_by` = the user, or a COMPANY member of the internship's company. FACULTY own the internships they posted.
- **Application visibility for staff:** the internship is owned by them.

#### auth (WP2)

| Method | Path | Who | Notes |
|---|---|---|---|
| POST | /auth/register/student | public | creates user (STUDENT) + students row, sends verification email; 201 `MessageResponse` |
| POST | /auth/register/company | public [EXT] | creates company (PENDING) + COMPANY user; needs admin approval of company before posting |
| POST | /auth/login | public | 200 `TokenResponse`, sets cookies. Unverified email → 403 EMAIL_NOT_VERIFIED. Inactive → 403 ACCOUNT_DEACTIVATED. Writes `login_events` |
| POST | /auth/refresh | cookie | rotates; 200 `TokenResponse` |
| POST | /auth/logout | cookie | revokes family; clears cookies; 204 |
| POST | /auth/verify-email | public | `{token}` → 200 |
| POST | /auth/resend-verification | public | `{email}` → 202 always |
| POST | /auth/forgot-password | public | `{email}` → 202 always |
| POST | /auth/reset-password | public | `{token,new_password}` → 200; revokes all refresh tokens |
| GET | /auth/me | any | `Me` |
| POST | /auth/change-password | any | `{current_password,new_password}` → 200 |

#### users (WP2)

| Method | Path | Who |
|---|---|---|
| GET | /users?role&q&is_active&page&page_size | A |
| POST | /users (any role, including FACULTY; marks verified when `mark_verified=true`) | A |
| GET | /users/{id} | A |
| PATCH | /users/{id} (full_name, phone, role-specific profile) | A |
| POST | /users/{id}/deactivate `{reason}` / /users/{id}/activate | A (cannot deactivate self) |
| POST | /users/bulk `{ids, action: "deactivate"\|"activate"}` [EXT] | A |
| PATCH | /users/me `{full_name, phone, avatar_url}` | any |

#### students (WP3)

| Method | Path | Who |
|---|---|---|
| GET | /students?q&department&gpa_min&gpa_max&page | A, F (F only sees students who applied to own internships) |
| GET | /students/me | S (profile + stats + default resume) |
| PATCH | /students/me (phone, department, gpa, skills, bio, links, graduation_year) | S |
| PUT | /students/me/resume `{document_id}` (set default resume) | S |
| GET | /students/{id} | A; F/C if the student applied to their internship |
| PATCH | /students/{id} | A |
| POST | /students/{id}/deactivate `{reason}` | A (spec: "deactivate student account") |
| GET | /students/{id}/applications | A, S(self) — application history |

#### faculty (WP3)

`GET /faculty` (A), `GET /faculty/me` (F), `PATCH /faculty/me` (F).

#### companies (WP3)

| Method | Path | Who |
|---|---|---|
| GET | /companies?q&location&industry&status&page | any auth (S sees ACTIVE only) |
| POST | /companies | A, F (status ACTIVE) |
| GET | /companies/{id} | any auth (detail + `rating_summary` + `internship_count`) |
| PATCH | /companies/{id} | A; F who created it; C member |
| POST | /companies/{id}/approve | A (PENDING → ACTIVE) [EXT] |
| POST | /companies/{id}/archive / restore | A (spec: archive) |
| DELETE | /companies/{id} | A; hard delete only if no internships, else 409 IN_USE (spec: "remove") |
| GET | /companies/{id}/internships | any auth (S: open only) |
| GET | /companies/{id}/ratings | any auth (averages per dimension + recent comments, anonymised where flagged) |
| GET | /companies/{id}/members | A, C(member) |

#### internships (WP3)

| Method | Path | Who |
|---|---|---|
| GET | /internships | any auth. Query: `q, domain (multi), company_id (multi), location, work_mode, stipend_min, stipend_max, duration_min, duration_max, status, mine (bool), include_archived, sort=relevance\|newest\|stipend_desc\|deadline_asc, page, page_size`. S: only APPROVED, not archived, deadline > now. F/C: open + own (any status) when `mine=true`. A: all |
| GET | /internships/facets | any auth → `{domains:[{value,count}], locations:[...], companies:[{id,name,count}], stipend:{min,max}, work_modes:[...]}` |
| POST | /internships `{..., submit: bool}` | F, C (company must be ACTIVE), A. Status DRAFT, or PENDING_APPROVAL if `submit` (A creates APPROVED directly) |
| GET | /internships/{id} | any auth (S: only if visible or already applied). Includes `company`, `is_saved`, `my_application` (S), `application_count` (owner/A) |
| PATCH | /internships/{id} | owner, A. Non-admin edit of core fields (title, description, dates, stipend, duration) on APPROVED → back to PENDING_APPROVAL |
| POST | /internships/{id}/submit | owner (DRAFT\|REJECTED → PENDING_APPROVAL) |
| POST | /internships/{id}/approve | A (PENDING_APPROVAL → APPROVED) |
| POST | /internships/{id}/reject `{reason}` | A |
| POST | /internships/{id}/close | owner, A (APPROVED → CLOSED) |
| POST | /internships/{id}/archive / restore | owner (archive only), A |
| DELETE | /internships/{id} | A; only if 0 applications, else 409 IN_USE |
| POST | /internships/bulk `{ids, action: approve\|reject\|archive\|close, reason?}` [EXT] | A |
| POST / DELETE | /internships/{id}/save [EXT] | S |
| GET | /internships/saved [EXT] | S |
| GET | /internships/{id}/applications?status&q&page | owner, A |

#### applications (WP3)

| Method | Path | Who |
|---|---|---|
| POST | /applications `{internship_id, resume_document_id, cover_letter, qualifications, answers}` | S. Checks, in order: email verified; internship APPROVED, not archived, `deadline > now` else 409 INTERNSHIP_NOT_OPEN / DEADLINE_PASSED; resume document owned, kind RESUME, status UPLOADED, PDF, <= 5 MB else 422 RESUME_INVALID; missing → 422 RESUME_REQUIRED; GPA >= min_gpa and department eligible else 422 INELIGIBLE; insert; IntegrityError on unique → 409 DUPLICATE_APPLICATION |
| GET | /applications?status&internship_id&q&page | S own; F/C own internships; A all |
| GET | /applications/{id} | S own, owner, A → `ApplicationDetail` (timeline, interviews, shared evaluations, feedback flags) |
| PATCH | /applications/{id}/status `{status, note?, offer_details?}` | owner, A (state machine) |
| POST | /applications/bulk-status `{ids, status, note?}` [EXT] | owner (all ids must be owned), A; returns `{updated:[ids], failed:[{id,code}]}` |
| POST | /applications/{id}/withdraw `{reason?}` | S own |
| DELETE | /applications/{id} | S own (alias of withdraw; spec "Delete: Withdraw") |
| POST | /applications/{id}/complete | owner, A |
| GET | /applications/{id}/resume-url | S own, owner, A → `{url, expires_in}` (presigned GET, 5 min) |

#### interviews (WP3)

| Method | Path | Who |
|---|---|---|
| POST | /interviews `{application_id, scheduled_at, duration_minutes, mode, location?, meeting_link?, interviewer_name, interviewer_email?, interviewer_user_id?}` | owner, A (rules R1–R5) |
| GET | /interviews?from&to&status&application_id&page | S own; F/C own internships or interviewer; A all |
| GET | /interviews/{id} | same scope (S does not see `comments`) |
| PATCH | /interviews/{id}/reschedule `{scheduled_at, duration_minutes?, reason}` | owner, A (R1–R4) |
| PATCH | /interviews/{id}/result `{status: COMPLETED\|NO_SHOW, result, score?, comments?, feedback_for_student?}` | owner, interviewer, A |
| POST | /interviews/{id}/cancel `{reason}` | owner, A |
| DELETE | /interviews/{id} | owner, A (alias of cancel) |

#### evaluations (WP3)

| Method | Path | Who |
|---|---|---|
| GET | /evaluation-forms | A, F, C |
| POST | /evaluation-forms `{name, description, criteria:[{name, description?, weight, max_score}]}` | A, F |
| GET / PATCH | /evaluation-forms/{id} | A, F (PATCH: creator or A; criteria are replaced only if no evaluations use the form, else 409 IN_USE) |
| POST | /evaluation-forms/{id}/archive | creator, A |
| POST | /evaluations `{form_id, application_id, scores:[{criterion_id, score, comment?}], overall_comments?, recommendation, shared_with_student}` | F owner, C owner, A. All criteria required |
| GET | /evaluations?application_id&internship_id&student_id&page | F/C own, A; S own and `shared_with_student` only |
| GET / PATCH | /evaluations/{id} | evaluator, A (PATCH recomputes weighted_score) |
| POST | /evaluations/{id}/archive | evaluator, A |
| DELETE | /evaluations/{id} | A (hard delete; spec "remove") |

#### feedback (WP3)

| Method | Path | Who |
|---|---|---|
| POST | /feedback/student | S (eligibility in 3.11) |
| GET | /feedback/student?company_id&internship_id&page | S own; F/C own internships; A all |
| GET | /feedback/student/trends?company_id&internship_id&months=12 | A, F, C → monthly averages per dimension |
| POST | /feedback/student/{id}/response `{body}` | F owner, C owner, A (spec: "view and respond to student feedback") |
| POST | /feedback/company | C member, F owner, A; application must be ACCEPTED |
| GET | /feedback/company?application_id&student_id&page | S (about self), F/C own, A |
| POST | /feedback/faculty | F (own internship), A |
| GET | /feedback/faculty?internship_id&page | F own, A |
| POST | /feedback/system | any auth |
| GET | /feedback/system?type&status&page | A all; others own |
| GET | /feedback/system/summary | A → counts by type/status, last 30 days trend |
| PATCH | /feedback/system/{id} `{status?, priority?, admin_notes?}` | A |
| POST | /feedback/system/{id}/action-items `{title, assignee_id?, due_date?}` | A |
| PATCH | /feedback/action-items/{id} `{status?, title?, due_date?}` | A |

#### documents [EXT] (WP3)

| Method | Path | Who |
|---|---|---|
| POST | /documents/upload-url `{kind, filename, content_type, size_bytes}` | any auth. RESUME: content_type must be application/pdf, size <= 5 242 880, else 422. Creates PENDING_UPLOAD row → `UploadTicket` |
| POST | /documents/{id}/complete | owner. HEAD object (exists, size matches, <= limit); read first 5 bytes == `%PDF-` for PDFs; else delete object, status REJECTED, 422 RESUME_INVALID → `Document` |
| GET | /documents?kind&owner_id&verification_status&page | own; A all |
| GET | /documents/{id}/download-url | owner; A; staff who own an internship the document's application targets |
| DELETE | /documents/{id} | owner (409 IN_USE if referenced by a non-withdrawn application), A |
| PATCH | /documents/{id}/verification `{verification_status, note?}` | A (feeds the compliance report "document verification status") |

#### notifications (WP4)

- `GET /notifications?unread_only&page`
- `GET /notifications/unread-count` → `{count}`
- `POST /notifications/{id}/read`
- `POST /notifications/read-all`
- `DELETE /notifications/{id}`

All of the above are own only. WebSocket `GET /api/v1/ws?token=<access_jwt>` is described in 6.10.

#### reports (WP4)

| Method | Path | Who |
|---|---|---|
| GET | /reports | any → `ReportMeta[]` available to the caller's role |
| GET | /reports/{key}?from&to&internship_id&company_id | role-gated (below) → `ReportData` |
| POST | /reports/{key}/export `{format: "pdf"\|"xlsx", params}` | same gate → 202 `Job` |
| GET | /jobs/{id} | requester, A → `Job` (`download_url` when SUCCEEDED) |
| GET | /jobs?type&page | A all; others own |

Report keys and gates:
- ADMIN: `placement-summary`, `application-analytics`, `student-performance`, `company-statistics`, `system-activity`, `compliance`
- FACULTY and COMPANY (scoped to own): `posted-internships`, `application-review`, `student-evaluations`, `interview-statistics`
- STUDENT: `my-applications`, `interview-schedule`, `placement-status`

ADMIN may also call the faculty keys unscoped and the student keys with `student_id`.

#### analytics (WP4)

`GET /analytics/dashboard` returns `DashboardData` for the caller's role. It is cached in Redis for 60 s per user.

#### admin (WP4)

| Method | Path | Who |
|---|---|---|
| GET | /admin/health | A → db/redis/minio/celery status + latency, queue depth, disk usage of buckets |
| GET | /admin/metrics?minutes=60 | A → per-minute request count, error count, p50/p95 latency (from Redis written by middleware) |
| GET | /admin/audit-logs?actor_id&entity_type&action&from&to&page | A |
| GET / POST | /admin/compliance/policies; PATCH /admin/compliance/policies/{id} | A |
| GET | /admin/compliance/violations?status&policy_code&page; PATCH /admin/compliance/violations/{id} `{status, note}` | A |
| POST | /admin/compliance/scan | A → 202 Job |
| POST | /admin/export `{entity: students\|companies\|internships\|applications\|feedback, format: csv\|xlsx, filters}` | A → 202 Job |
| POST | /admin/import (multipart `entity`, `file` .csv/.xlsx <= 5 MB) | A → 202 Job (row-level validation with the same Pydantic schemas; result lists errors) |
| GET | /admin/import/template/{entity} | A → xlsx template download |

#### health (WP2, no auth, no prefix)

- `GET /healthz` → `{status:"ok"}` (liveness)
- `GET /readyz` → checks db and redis, returns 503 if either is down

---

## 5. Frontend

### 5.1 Route map (App Router, `src/app`)

`proxy.ts` rules:
- No `ch_refresh` cookie on an `(app)` route → redirect to `/login?next=`.
- `/student/*` requires role STUDENT, `/faculty/*` FACULTY, `/company/*` COMPANY, `/admin/*` ADMIN. Otherwise redirect to `/dashboard`.
- Logged-in users hitting `/login` or `/register` → `/dashboard`.

| Route | Owner | Roles | Page |
|---|---|---|---|
| `/` | WP5 | public | Landing: hero, features, role cards, CTA |
| `/login`, `/register`, `/register/company`, `/verify-email?token=`, `/forgot-password`, `/reset-password?token=` | WP5 | public | Auth pages (split layout, brand panel) |
| `/dashboard` | WP5 | all | server redirect to `/{role}` |
| `/notifications` | WP5 | all | Notifications center (tabs All/Unread, mark read) [EXT] |
| `/profile` | WP5 | all | Profile edit (role-specific fields; student: GPA, dept, skills, links, default resume) |
| `/settings` | WP5 | all | Theme, password change, sessions (logout everywhere) |
| `/feedback/system` | WP5 | all | Submit feature, bug or improvement + my submissions |
| `/internships` | WP6 | all | **Internship explorer**: search bar, instant filters (domain chips, company combobox, location, work mode, stipend range slider, duration), sort, grid/list toggle, URL-synced state, skeletons, infinite or paginated |
| `/internships/[id]` | WP6 | all | **Internship detail**: header (company logo, title, badges), overview, skills, eligibility, timeline (deadline, start/end), company card with rating, sticky apply/save panel; owner/admin see status + actions |
| `/internships/[id]/apply` | WP6 | S | **5-step application wizard** (see 5.4) |
| `/documents` | WP6 | all | Documents center: upload (PDF resume), list, set default, download, delete, verification badge [EXT] |
| `/student` | WP6 | S | **Student dashboard**: KPIs, application timeline stepper per active app, upcoming interviews, recommended internships, profile completeness |
| `/student/applications` | WP6 | S | My applications table/cards + status filter |
| `/student/applications/[id]` | WP6 | S | Application detail: full timeline stepper, interviews, shared evaluations, offer, withdraw |
| `/student/saved` | WP6 | S | Saved internships [EXT] |
| `/student/interviews` | WP6 | S | Interview center (calendar + list, results) |
| `/student/feedback` | WP6 | S | Feedback center: pending post-internship feedback, submitted, company feedback received |
| `/student/reports` | WP6 | S | My Applications / Interview Schedule / Placement Status reports + export |
| `/faculty` | WP7 | F | Faculty dashboard: KPIs, applications needing review, upcoming interviews, my postings |
| `/faculty/internships` | WP7 | F | My postings table (status, applicants, actions) |
| `/faculty/internships/new`, `/faculty/internships/[id]/edit` | WP7 | F | Internship form (RHF + Zod, date pickers, computed duration) |
| `/faculty/review/[internshipId]` | WP7 | F | **Split-screen candidate review**: left = applicant list (filter, bulk select, bulk status); right = candidate panel (profile, resume PDF iframe via presigned URL, cover letter, qualifications, history, actions: under review / shortlist / reject / accept with offer / schedule interview / evaluate) |
| `/faculty/interviews` | WP7 | F | Interview center (calendar week/month, schedule dialog enforcing 24h + deadline, reschedule, cancel, record result) |
| `/faculty/evaluations` | WP7 | F | **Evaluation center**: list, evaluate dialog with **slider per criterion**, live weighted score, forms tab (create/edit forms) |
| `/faculty/feedback` | WP7 | F | Student feedback on my internships (respond), faculty feedback form, company feedback |
| `/faculty/reports` | WP7 | F | 4 faculty reports + export |
| `/faculty/companies` | WP7 | F | Company list + create |
| `/company`, `/company/internships`, `/company/internships/new`, `/company/internships/[id]/edit`, `/company/review/[internshipId]`, `/company/interviews`, `/company/evaluations`, `/company/feedback`, `/company/reports`, `/company/profile` | WP7 | C | Company portal [EXT]; reuses the faculty feature components with `scope="company"` |
| `/companies/[id]` | WP7 | all | **Company profile**: banner, details, contact, ratings radar + trend, open internships, reviews |
| `/admin` | WP7 | A | **Admin control center**: KPI row, charts (applications over time, status donut, placements by department, top companies), pending approvals, system health strip, recent audit |
| `/admin/users` | WP7 | A | Users table (role filter, search, create user dialog, activate/deactivate, bulk) |
| `/admin/companies` | WP7 | A | Companies table (approve, archive, restore, delete) |
| `/admin/internships` | WP7 | A | Approval queue + all internships (bulk approve/reject) |
| `/admin/applications` | WP7 | A | All applications table |
| `/admin/reports`, `/admin/reports/[key]` | WP7 | A | 6 admin reports + export PDF/XLSX (job polling) |
| `/admin/compliance` | WP7 | A | Policies, violations, document verification queue, run scan |
| `/admin/data` | WP7 | A | Import (template download, upload, job result errors) / Export |
| `/admin/system` | WP7 | A | System health + metrics charts |
| `/admin/audit` | WP7 | A | Audit log viewer |
| `/admin/feedback` | WP7 | A | System feedback triage board (status columns) + action items |

### 5.2 Design tokens (`src/app/globals.css`, WP5)

- Font: `Geist` and `Geist_Mono` via `next/font/google`, exposed as `--font-sans` and `--font-mono`.
- Primary indigo. Light: `--primary: oklch(0.511 0.262 276.966)` (indigo-600), `--primary-foreground: oklch(0.985 0 0)`. Dark: `--primary: oklch(0.585 0.233 277.117)` (indigo-500).
- Neutrals use the zinc scale (shadcn "zinc" base). `--background` is `oklch(1 0 0)` in light and `oklch(0.141 0.005 285.823)` in dark.
- Radius: `--radius: 0.75rem` (12px). Use `rounded-xl` (12px) for inputs/buttons and `rounded-2xl` (16px) for cards, dialogs and the sidebar.
- Shadow: cards use `shadow-sm` plus a `border-border/60` hairline. Elevated surfaces (popover, dialog) use `shadow-lg`.
- Status palette (`lib/status.ts`, `StatusBadge`), applied as soft badge `bg-*/10 text-*-600 dark:text-*-400 ring-1 ring-*/20`:

| Status | Color |
|---|---|
| PENDING | slate |
| UNDER_REVIEW | sky |
| SHORTLISTED | violet |
| INTERVIEW | amber |
| ACCEPTED | emerald |
| REJECTED | rose |
| WITHDRAWN | zinc |
| DRAFT | zinc |
| PENDING_APPROVAL | amber |
| APPROVED | emerald |
| REJECTED (internship) | rose |
| CLOSED | slate |

- Chart palette (ECharts theme `campushire`): `#6366F1, #22C55E, #F59E0B, #06B6D4, #EC4899, #8B5CF6, #64748B`. A dark variant swaps the axis and label colours.
- Motion: `motion/react` page transitions (fade + 8px rise, 180 ms), list stagger 30 ms, `prefers-reduced-motion` respected.
- Layout:
  - Sidebar 264px (collapsible to 72px, state in localStorage).
  - Topbar 56px with search trigger (Ctrl+K), notification bell, theme toggle, user menu.
  - Content `max-w-7xl` with `px-4 md:px-8`.
  - Mobile: the sidebar becomes a Sheet.
- Dark mode [EXT]: `next-themes`, `attribute="class"`, default `system`.

### 5.3 Component inventory

**`components/ui` (WP5)** is generated with the shadcn CLI:

```
accordion alert alert-dialog avatar badge breadcrumb button calendar card checkbox collapsible
command dialog dropdown-menu form hover-card input input-otp label pagination popover progress
radio-group scroll-area select separator sheet sidebar skeleton slider sonner switch table tabs
textarea toggle toggle-group tooltip chart(not used: we use ECharts)
```

**`components/layout` (WP5):**
- `AppShell`
- `AppSidebar` (role-aware from `lib/nav.ts`)
- `Topbar`
- `CommandPalette` [EXT] (cmdk: navigation for role, quick actions, internship search via `/internships?q=` debounce)
- `NotificationBell` (unread count + popover list, realtime)
- `ThemeToggle`
- `UserMenu`
- `PageTransition`

**`components/shared` (WP5)** (every page uses these, so they ship before Wave B):

| Component | Purpose |
|---|---|
| `PageHeader({title, description, actions, breadcrumbs})` | |
| `StatCard({label, value, delta?, icon, format})` | |
| `DataTable<T>({columns, data, total, page, pageSize, onPageChange, selectable, onSelectionChange, toolbar, loading, emptyState})` | TanStack Table v8 (`@tanstack/react-table`) |
| `BulkActionBar({count, actions})` [EXT] | |
| `StatusBadge({status})` | |
| `EmptyState({icon, title, description, action})` | |
| `ConfirmDialog` | |
| `ErrorState` | |
| `LoadingSkeletons` (card/table/list) | |
| `FileUpload({kind, accept, maxBytes, onUploaded})` | presigned POST flow: request ticket → `FormData` POST to MinIO with progress (XHR) → `/complete`; client checks type `application/pdf` and size <= 5 MB first |
| `PdfViewer({documentId})` | fetches download-url, renders `<iframe>` |
| `RatingInput({value, onChange, max=5})` | stars, keyboard accessible |
| `RatingDisplay` | |
| `ScoreSlider({criterion, value, onChange})` | |
| `Stepper({steps, current, orientation})` | |
| `ApplicationTimeline({events})` | vertical, icons per status |
| `Chart({option, height})` | ECharts wrapper with theme, resize observer, dark mode |
| `CalendarView({events, view: "month"\|"week", onSelectEvent, onSelectSlot})` | custom with date-fns; no external calendar lib |
| `DateTimePicker`, `DateRangePicker` | |
| `SearchInput` | debounced |
| `FacetFilter` | multi-select popover |
| `RangeSlider` | |
| `CompanyLogo` | |
| `UserAvatar` | |
| `KeyValueList` | |
| `ReportViewer({report: ReportData})` | KPI row + charts + tables; used by all report pages |
| `ExportButton({reportKey, params})` | creates job, polls `/jobs/{id}` every 2 s, downloads |
| `RoleGate({roles, children})` | |

**Feature components:**
- WP6: `InternshipCard`, `InternshipFilters`, `ApplyWizard` + 5 step components, `ApplicationCard`, `StudentKpis`, `RecommendedInternships`, `StudentInterviewList`, `StudentFeedbackForm` (5 ratings + comments), `ResumeManager`.
- WP7: `InternshipForm`, `CandidateList`, `CandidatePanel`, `StatusActionMenu`, `OfferDialog`, `ScheduleInterviewDialog` (client checks 24h + deadline), `InterviewResultDialog`, `EvaluationDialog`, `EvaluationFormBuilder`, `CompanyForm`, `CompanyRatingsRadar`, `FeedbackTrendChart`, `CompanyFeedbackForm` (6 ratings + hire likelihood), `FacultyFeedbackForm`, `RespondDialog`, `AdminKpis`, `ApprovalQueue`, `UserTable`, `CreateUserDialog`, `HealthPanel`, `MetricsCharts`, `AuditTable`, `ViolationTable`, `ImportWizard`, `ExportPanel`, `FeedbackBoard`, `ActionItemList`.

### 5.4 Application wizard (WP6)

Five steps, with state in RHF and a per-step Zod schema. "Next" validates the current step only. The draft is kept in localStorage per internship.

1. **Overview & eligibility:** internship summary, eligibility check (GPA, department, deadline countdown). Blocks if ineligible.
2. **Resume:** choose an existing uploaded resume or upload a new PDF (FileUpload, 5 MB). Required.
3. **Cover letter:** textarea 50–5000 chars with counter.
4. **Qualifications:** summary textarea (10–3000), skills tag input, relevant coursework, availability date, portfolio URL. These go to `answers`.
5. **Review & submit:** read-only summary and a confirm checkbox. Submit calls `POST /applications`. On 409 DUPLICATE_APPLICATION, show a toast and redirect to the existing application. On success, show a confetti-free success screen and a link to the application.

### 5.5 Data layer (WP5)

- `lib/api/client.ts`: `apiFetch<T>(path, {method, body, query, signal})`.
  - Base `process.env.NEXT_PUBLIC_API_URL + "/api/v1"`.
  - Sends `credentials: "include"` and attaches the in-memory access token.
  - On 401 `TOKEN_EXPIRED`, makes a single-flight `POST /auth/refresh` (with the `X-Requested-With` header) and retries once. If refresh fails, it clears the session and redirects to `/login`.
  - Throws `ApiError {status, code, message, details}`.
- On app boot, `AuthProvider` calls `/auth/refresh` to get an access token and `Me`. While that runs, it shows a full-screen skeleton.
- `lib/api/endpoints/<module>.ts` holds typed functions per endpoint in section 4. `lib/api/hooks/<module>.ts` holds TanStack Query hooks with key factory `qk.<module>.<op>(params)`. Mutations invalidate the related keys.
- Forms map `ApiError.details` to RHF `setError(field)`.
- `lib/validation/*.ts`: Zod schemas mirroring the backend rules. Each rule in section 8.1 has a matching Zod rule:
  - `passwordSchema` (regex `^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,128}$`)
  - `phoneSchema` (`^\+?[1-9]\d{9,14}$` after stripping spaces and dashes)
  - `gpaSchema`
  - `registrationNumberSchema`
  - `internshipSchema` (dates future, start < end, 28–183 days, deadline < start)
  - `ratingSchema` (int 1–5)
  - `interviewSchema` (>= now + 24h, <= deadline)

---

## 6. API CONTRACT (shared source of truth)

`frontend/src/lib/api/types.ts` (WP5) and the backend `schemas.py` files (WP2/3/4) must match this section **exactly**. Request field names are the same as the response field names unless stated otherwise. Optional fields are marked `?`. `null` means the field is present but nullable.

### 6.1 Common

```ts
export type UUID = string; export type ISODateTime = string; export type ISODate = string;
export type Role = "ADMIN" | "FACULTY" | "STUDENT" | "COMPANY";
export interface Page<T> { items: T[]; total: number; page: number; page_size: number; pages: number; }
export interface ApiErrorBody { error: { code: string; message: string; details?: { field: string; message: string }[]; request_id?: string } }
export interface MessageResponse { message: string }
export type ApplicationStatus = "PENDING"|"UNDER_REVIEW"|"SHORTLISTED"|"INTERVIEW"|"ACCEPTED"|"REJECTED"|"WITHDRAWN";
export type InternshipStatus = "DRAFT"|"PENDING_APPROVAL"|"APPROVED"|"REJECTED"|"CLOSED";
export type CompanyStatus = "PENDING"|"ACTIVE"|"ARCHIVED";
export type WorkMode = "ONSITE"|"REMOTE"|"HYBRID";
export type InterviewStatus = "SCHEDULED"|"RESCHEDULED"|"COMPLETED"|"CANCELLED"|"NO_SHOW";
export type InterviewResult = "PENDING"|"PASS"|"FAIL"|"ON_HOLD";
export type InterviewMode = "ONLINE"|"ONSITE"|"PHONE";
export type DocumentKind = "RESUME"|"COVER_LETTER"|"TRANSCRIPT"|"OFFER_LETTER"|"LOGO"|"REPORT"|"EXPORT"|"IMPORT"|"OTHER";
export type JobStatus = "QUEUED"|"RUNNING"|"SUCCEEDED"|"FAILED";
```

### 6.2 Auth and users

```ts
export interface StudentRegisterRequest { email: string; password: string; full_name: string; phone: string; department: string; gpa: number; enrollment_no?: string; graduation_year?: number }
export interface CompanyRegisterRequest { email: string; password: string; full_name: string; phone?: string; job_title?: string;
  company: { name: string; registration_number: string; location: string; industry?: string; website?: string; contact_person_name: string; contact_email: string; contact_phone?: string } }
export interface LoginRequest { email: string; password: string }
export interface Me { id: UUID; email: string; role: Role; full_name: string; phone: string|null; avatar_url: string|null; email_verified: boolean; is_active: boolean; created_at: ISODateTime;
  student?: StudentProfile; faculty?: FacultyProfile; company?: { company_id: UUID; company_name: string; company_status: CompanyStatus; job_title: string|null } }
export interface TokenResponse { access_token: string; token_type: "bearer"; expires_in: number; user: Me }
export interface UserSummary { id: UUID; email: string; role: Role; full_name: string; phone: string|null; is_active: boolean; email_verified: boolean; last_login_at: ISODateTime|null; created_at: ISODateTime }
export interface AdminCreateUserRequest { email: string; password: string; full_name: string; role: Role; phone?: string; mark_verified?: boolean;
  student?: { department: string; gpa: number; enrollment_no?: string; graduation_year?: number };
  faculty?: { department: string; designation?: string; employee_id?: string };
  company?: { company_id: UUID; job_title?: string } }
export interface UpdateUserRequest { full_name?: string; phone?: string|null; student?: Partial<StudentProfileUpdate>; faculty?: Partial<FacultyProfile> }
```

### 6.3 Students, faculty, companies

```ts
export interface StudentProfile { user_id: UUID; department: string; gpa: number; enrollment_no: string|null; graduation_year: number|null; skills: string[]; bio: string|null;
  linkedin_url: string|null; github_url: string|null; portfolio_url: string|null; default_resume: DocumentSummary|null }
export interface StudentProfileUpdate { phone?: string; department?: string; gpa?: number; graduation_year?: number|null; skills?: string[]; bio?: string|null; linkedin_url?: string|null; github_url?: string|null; portfolio_url?: string|null }
export interface StudentListItem { user_id: UUID; full_name: string; email: string; phone: string|null; department: string; gpa: number; is_active: boolean; application_count: number; placed: boolean }
export interface StudentDetail extends StudentListItem { profile: StudentProfile; stats: { total_applications: number; by_status: Record<ApplicationStatus, number>; interviews_upcoming: number } }
export interface FacultyProfile { user_id: UUID; department: string; designation: string|null; employee_id: string|null }
export interface CompanySummary { id: UUID; name: string; registration_number: string; industry: string|null; location: string; logo_url: string|null; status: CompanyStatus; avg_rating: number|null; rating_count: number; open_internships: number }
export interface Company extends CompanySummary { website: string|null; description: string|null; contact_person_name: string; contact_email: string; contact_phone: string|null; archived_at: ISODateTime|null; created_at: ISODateTime;
  rating_summary: RatingSummary }
export interface CompanyCreateRequest { name: string; registration_number: string; location: string; industry?: string; website?: string; description?: string; contact_person_name: string; contact_email: string; contact_phone?: string; logo_document_id?: UUID }
export interface RatingSummary { count: number; overall: number|null; company_culture: number|null; mentorship: number|null; technical_learning: number|null; work_environment: number|null;
  distribution: Record<"1"|"2"|"3"|"4"|"5", number> }
```

### 6.4 Internships

```ts
export interface InternshipSummary { id: UUID; title: string; domain: string; location: string; work_mode: WorkMode; stipend_monthly: number; currency: string;
  duration_weeks: number; start_date: ISODate; end_date: ISODate; application_deadline: ISODateTime; status: InternshipStatus; skills: string[];
  company: { id: UUID; name: string; logo_url: string|null; avg_rating: number|null }; is_saved: boolean; application_count?: number; archived_at: ISODateTime|null; created_at: ISODateTime }
export interface Internship extends InternshipSummary { description: string; openings: number; min_gpa: number|null; eligible_departments: string[];
  posted_by: { id: UUID; full_name: string; role: Role }; rejection_reason: string|null; approved_at: ISODateTime|null;
  my_application: { id: UUID; status: ApplicationStatus } | null; can_edit: boolean; can_apply: boolean }
export interface InternshipCreateRequest { company_id: UUID; title: string; description: string; domain: string; location: string; work_mode: WorkMode; stipend_monthly: number; currency?: string;
  duration_weeks?: number; start_date: ISODate; end_date: ISODate; application_deadline: ISODateTime; openings?: number; skills?: string[]; min_gpa?: number|null; eligible_departments?: string[]; submit?: boolean }
export type InternshipUpdateRequest = Partial<Omit<InternshipCreateRequest,"company_id"|"submit">>;
export interface InternshipFacets { domains: {value: string; count: number}[]; locations: {value: string; count: number}[]; companies: {id: UUID; name: string; count: number}[];
  work_modes: {value: WorkMode; count: number}[]; stipend: { min: number; max: number } }
export interface BulkActionResult { updated: UUID[]; failed: { id: UUID; code: string; message: string }[] }
```

### 6.5 Applications

```ts
export interface ApplicationCreateRequest { internship_id: UUID; resume_document_id: UUID; cover_letter: string; qualifications: string;
  answers?: { skills?: string[]; coursework?: string; availability_from?: ISODate; portfolio_url?: string } }
export interface ApplicationSummary { id: UUID; status: ApplicationStatus; status_changed_at: ISODateTime; created_at: ISODateTime;
  internship: { id: UUID; title: string; company_id: UUID; company_name: string; company_logo_url: string|null; application_deadline: ISODateTime; start_date: ISODate };
  student: { id: UUID; full_name: string; email: string; department: string; gpa: number }; next_interview_at: ISODateTime|null; evaluation_avg: number|null }
export interface TimelineEvent { at: ISODateTime; kind: "STATUS"|"INTERVIEW_SCHEDULED"|"INTERVIEW_RESCHEDULED"|"INTERVIEW_CANCELLED"|"INTERVIEW_COMPLETED"|"EVALUATION"|"COMPLETED";
  status?: ApplicationStatus; title: string; note: string|null; actor_name: string|null }
export interface ApplicationDetail extends ApplicationSummary { cover_letter: string; qualifications: string; answers: Record<string, unknown>; resume: DocumentSummary;
  decision_note: string|null; offer_details: OfferDetails|null; withdrawn_reason: string|null; completed_at: ISODateTime|null;
  timeline: TimelineEvent[]; interviews: Interview[]; evaluations: EvaluationSummary[];
  allowed_transitions: ApplicationStatus[];   // computed for the caller
  can_give_student_feedback: boolean; student_feedback_id: UUID|null; company_feedback_ids: UUID[] }
export interface OfferDetails { stipend_monthly: number; start_date: ISODate; joining_location?: string; notes?: string }
export interface ApplicationStatusUpdateRequest { status: ApplicationStatus; note?: string; offer_details?: OfferDetails }
export interface BulkStatusRequest { ids: UUID[]; status: ApplicationStatus; note?: string }
```

### 6.6 Interviews

```ts
export interface Interview { id: UUID; application_id: UUID; scheduled_at: ISODateTime; duration_minutes: number; mode: InterviewMode; location: string|null; meeting_link: string|null;
  interviewer_name: string; interviewer_email: string|null; status: InterviewStatus; result: InterviewResult; score: number|null;
  comments?: string|null;            // omitted for STUDENT
  feedback_for_student: string|null; cancel_reason: string|null; reschedule_count: number;
  student: { id: UUID; full_name: string }; internship: { id: UUID; title: string; company_name: string }; created_at: ISODateTime }
export interface InterviewCreateRequest { application_id: UUID; scheduled_at: ISODateTime; duration_minutes: number; mode: InterviewMode; location?: string; meeting_link?: string;
  interviewer_name: string; interviewer_email?: string; interviewer_user_id?: UUID }
export interface InterviewRescheduleRequest { scheduled_at: ISODateTime; duration_minutes?: number; reason: string }
export interface InterviewResultRequest { status: "COMPLETED"|"NO_SHOW"; result: InterviewResult; score?: number; comments?: string; feedback_for_student?: string }
```

### 6.7 Evaluations

```ts
export interface EvaluationCriterion { id: UUID; name: string; description: string|null; weight: number; max_score: 5|10; position: number }
export interface EvaluationForm { id: UUID; name: string; description: string|null; is_default: boolean; criteria: EvaluationCriterion[]; archived_at: ISODateTime|null; created_at: ISODateTime; in_use: boolean }
export interface EvaluationFormCreateRequest { name: string; description?: string; criteria: { name: string; description?: string; weight: number; max_score: 5|10 }[] }
export interface EvaluationSummary { id: UUID; form_name: string; evaluator_name: string; weighted_score: number; recommendation: "STRONG_YES"|"YES"|"MAYBE"|"NO"; created_at: ISODateTime; shared_with_student: boolean }
export interface Evaluation extends EvaluationSummary { form_id: UUID; application_id: UUID; student: { id: UUID; full_name: string }; internship: { id: UUID; title: string };
  scores: { criterion_id: UUID; criterion_name: string; score: number; max_score: number; weight: number; comment: string|null }[]; overall_comments: string|null; archived_at: ISODateTime|null }
export interface EvaluationCreateRequest { form_id: UUID; application_id: UUID; scores: { criterion_id: UUID; score: number; comment?: string }[]; overall_comments?: string;
  recommendation: "STRONG_YES"|"YES"|"MAYBE"|"NO"; shared_with_student?: boolean }
// weighted_score = 100 * Σ(score/max_score * weight) / Σ(weight), rounded to 2 decimals
```

### 6.8 Feedback

```ts
export interface StudentFeedbackCreateRequest { application_id: UUID; company_culture: number; mentorship: number; technical_learning: number; work_environment: number; overall: number; comments?: string; suggestions?: string; is_anonymous?: boolean }
export interface StudentFeedback extends StudentFeedbackCreateRequest { id: UUID; student_name: string|null /* null if anonymous and viewer is not ADMIN */; company: { id: UUID; name: string }; internship: { id: UUID; title: string };
  response_body: string|null; responded_by_name: string|null; responded_at: ISODateTime|null; created_at: ISODateTime }
export interface FeedbackTrends { months: string[] /* "2026-04" */; series: { dimension: "overall"|"company_culture"|"mentorship"|"technical_learning"|"work_environment"; values: (number|null)[] }[]; counts: number[] }
export interface CompanyFeedbackCreateRequest { application_id: UUID; technical_skills: number; soft_skills: number; punctuality: number; responsibility: number; teamwork: number; learning_ability: number; strengths?: string; improvements?: string; hire_likelihood: number }
export interface CompanyFeedback extends CompanyFeedbackCreateRequest { id: UUID; author_name: string; student: { id: UUID; full_name: string }; internship: { id: UUID; title: string }; average: number; created_at: ISODateTime }
export interface FacultyFeedbackCreateRequest { internship_id: UUID; application_id?: UUID; course_suitability: number; learning_outcomes: number; internship_quality: number; suggestions?: string; comments?: string }
export interface FacultyFeedback extends FacultyFeedbackCreateRequest { id: UUID; faculty_name: string; internship_title: string; created_at: ISODateTime }
export interface SystemFeedbackCreateRequest { type: "FEATURE"|"BUG"|"IMPROVEMENT"; title: string; description: string; page_url?: string; severity?: "LOW"|"MEDIUM"|"HIGH"|"CRITICAL" }
export interface SystemFeedback extends SystemFeedbackCreateRequest { id: UUID; user: { id: UUID; full_name: string; role: Role }; status: "NEW"|"TRIAGED"|"PLANNED"|"IN_PROGRESS"|"DONE"|"WONT_DO";
  priority: "LOW"|"MEDIUM"|"HIGH"|null; admin_notes: string|null; action_items: ActionItem[]; created_at: ISODateTime }
export interface ActionItem { id: UUID; title: string; assignee: { id: UUID; full_name: string }|null; status: "OPEN"|"IN_PROGRESS"|"DONE"; due_date: ISODate|null; created_at: ISODateTime }
export interface SystemFeedbackSummary { by_type: Record<string, number>; by_status: Record<string, number>; last_30_days: { date: ISODate; count: number }[]; open_action_items: number }
```

### 6.9 Documents, notifications, jobs

```ts
export interface UploadUrlRequest { kind: DocumentKind; filename: string; content_type: string; size_bytes: number }
export interface UploadTicket { document_id: UUID; upload: { url: string; fields: Record<string, string> }; expires_in: number; max_bytes: number }
// browser: const fd = new FormData(); Object.entries(fields).forEach(([k,v])=>fd.append(k,v)); fd.append("file", file); POST upload.url → 204; then POST /documents/{id}/complete
export interface DocumentSummary { id: UUID; kind: DocumentKind; filename: string; content_type: string; size_bytes: number; status: "PENDING_UPLOAD"|"UPLOADED"|"REJECTED";
  verification_status: "PENDING"|"VERIFIED"|"REJECTED"; created_at: ISODateTime }
export interface Document extends DocumentSummary { owner: { id: UUID; full_name: string }; verification_note: string|null; verified_at: ISODateTime|null; in_use: boolean }
export interface Notification { id: UUID; type: string; title: string; body: string; link: string|null; data: Record<string, unknown>; read_at: ISODateTime|null; created_at: ISODateTime }
export interface Job { id: UUID; type: "REPORT_EXPORT"|"DATA_EXPORT"|"DATA_IMPORT"|"COMPLIANCE_SCAN"; status: JobStatus; progress: number; params: Record<string, unknown>;
  result: { rows_ok?: number; rows_failed?: number; errors?: { row: number; field: string; message: string }[] } | null; error: string|null; download_url: string|null; created_at: ISODateTime; finished_at: ISODateTime|null }
```

### 6.10 WebSocket

- Connect to `ws://localhost:8000/api/v1/ws?token=<access_jwt>`. The server closes with 4401 on a bad or expired token. The client then refreshes and reconnects with backoff 1 s, 2 s, 5 s, 10 s (max).
- Server → client messages (JSON):
  - `{"type":"notification","data":Notification}`
  - `{"type":"unread_count","data":{"count":n}}`
  - `{"type":"job","data":Job}` (job progress for the requester)
  - `{"type":"ping"}` every 25 s
- Client → server: `{"type":"pong"}`.
- Server side: one Redis pub/sub subscription per socket on `user:{id}`. `side_effects.flush()` publishes after commit. Workers publish job updates the same way.
- On receiving a message, the frontend `RealtimeProvider` invalidates `qk.notifications.*` and, for `job`, updates `qk.jobs.detail(id)`. It also shows a sonner toast for notifications.

### 6.11 Reports and analytics

```ts
export interface ReportMeta { key: string; title: string; description: string; formats: ("pdf"|"xlsx")[]; params: ("from"|"to"|"internship_id"|"company_id"|"student_id")[] }
export type ReportChart =
  | { id: string; type: "line"|"bar"|"area"; title: string; x: string[]; series: { name: string; data: number[] }[] }
  | { id: string; type: "pie"|"donut"; title: string; data: { name: string; value: number }[] }
  | { id: string; type: "radar"; title: string; indicators: { name: string; max: number }[]; series: { name: string; data: number[] }[] };
export interface ReportTable { id: string; title: string; columns: { key: string; label: string; format?: "number"|"percent"|"currency"|"date"|"datetime"|"text" }[]; rows: Record<string, string|number|null>[] }
export interface Kpi { label: string; value: number|string; format?: "number"|"percent"|"currency"|"text"; delta?: number|null; hint?: string }
export interface ReportData { key: string; title: string; generated_at: ISODateTime; params: Record<string, unknown>; kpis: Kpi[]; charts: ReportChart[]; tables: ReportTable[] }
export interface DashboardData { role: Role; kpis: Kpi[]; charts: ReportChart[];
  lists: { id: string; title: string; items: { id: UUID; title: string; subtitle?: string; status?: string; at?: ISODateTime; link: string }[] }[] }
```

Required report contents (WP4 builders must produce at least these KPIs, charts and tables):

| Key | KPIs | Charts | Tables |
|---|---|---|---|
| placement-summary | placement rate % (students with ACCEPTED / active students), total students placed, average stipend (accepted offers, fallback to internship stipend), total offers | placements by department (bar), placements over time (line) | placed students |
| application-analytics | total applications, acceptance rate %, avg time to decision (days) | status breakdown (donut), applications per week (area) | by internship |
| student-performance | completion rate % (completed / accepted), avg evaluation score | top performing students (bar, by weighted_score), most popular internships (bar, by application count) | top 20 students |
| company-statistics | active companies, avg rating, feedback count | most active companies (bar: internships + applications), rating radar | company table with avg ratings + student feedback summary (count, avg overall, latest comment) |
| system-activity | registrations (period), logins (period), active users 7d, storage used MB, document count | registrations per day by role (line), login trends success/fail (line), storage by bucket (pie) | — |
| compliance | open violations, resolved, documents pending verification, verified % | violations by policy (bar), document verification status (donut) | open violations, pending documents |
| posted-internships | number of postings, total applications, avg applications per internship | status breakdown (donut, internship statuses), applications per internship (bar) | postings |
| application-review | reviewed (non-PENDING) vs pending, shortlisting rate % | reviewed vs pending (pie), funnel PENDING → SHORTLISTED → INTERVIEW → ACCEPTED (bar) | — |
| student-evaluations | evaluated students count, avg weighted score, avg per criterion | score distribution (bar) | evaluations + feedback summary |
| interview-statistics | scheduled, completed, success rate % (PASS / COMPLETED), no-show rate | interviews per week (bar), results (donut) | upcoming |
| my-applications | total, by status | status distribution (donut) | application timeline table (date, internship, status) |
| interview-schedule | upcoming count, completed count | — | upcoming, past results with feedback_for_student |
| placement-status | current status (Placed/In process/Not placed) | — | offer details (company, stipend, start date, location) |

---

## 7. Docker, env, seed

### 7.1 docker-compose.yml (WP1)

| service | image/build | ports (host:container) | notes |
|---|---|---|---|
| postgres | postgres:17-alpine | **5433:5432** (host 5432 is already used by a local Postgres, PID 8280) | env POSTGRES_DB=campushire, USER=campushire, PASSWORD=campushire; volume `pgdata`; mounts `./infra/postgres/init` to `/docker-entrypoint-initdb.d`; healthcheck `pg_isready -U campushire -d campushire` |
| redis | redis:7.4-alpine | 6379:6379 | `redis-server --appendonly yes`; healthcheck `redis-cli ping` |
| minio | pgsty/minio:RELEASE.2026-08-04T00-00-00Z | 9000:9000, 9001:9001 | `server /data --console-address ":9001"`; env MINIO_ROOT_USER=campushire, MINIO_ROOT_PASSWORD=campushire-secret, MINIO_API_CORS_ALLOW_ORIGIN=http://localhost:3000; volume `miniodata`; no healthcheck (the api entrypoint waits for it via boto3) |
| mailpit | axllent/mailpit:v1 | 1025:1025, 8025:8025 | |
| api | build ./backend | 8000:8000 | env_file .env; depends_on postgres(healthy), redis(healthy), minio(started), mailpit(started); entrypoint runs `entrypoint.sh`; CMD `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers`; healthcheck `python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/healthz')"` |
| worker | build ./backend (same image) | — | env_file .env; `RUN_MIGRATIONS=false SEED_DEMO=false`; command `celery -A app.workers.main worker -B -l info --concurrency 2`; depends_on api(healthy) |
| frontend | build ./frontend, args NEXT_PUBLIC_API_URL=http://localhost:8000, NEXT_PUBLIC_WS_URL=ws://localhost:8000 | 3000:3000 | depends_on api(healthy); CMD `node server.js` |

### 7.2 Dockerfiles

**backend/Dockerfile** (python:3.13-slim):
1. `PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1`.
2. Copy requirements and run `pip install -r requirements.txt -r requirements-dev.txt`. Dev deps are included so tests run in the container.
3. Copy the app.
4. `RUN sed -i 's/\r$//' docker/entrypoint.sh && chmod +x docker/entrypoint.sh`.
5. Run as a non-root user `app`.

**backend/docker/entrypoint.sh** (`#!/bin/sh`, `set -e`):
1. `python -m app.core.wait` waits for db, redis and minio (60 s max). WP2 provides `app/core/wait.py`.
2. If `RUN_MIGRATIONS=true`, run `alembic upgrade head`.
3. `python -c "from app.core.storage import ensure_buckets; ensure_buckets()"`.
4. If `SEED_DEMO=true`, run `python -m app.seed`.
5. `exec "$@"`.

**frontend/Dockerfile:** three stages (deps: `npm ci`; build: `ARG NEXT_PUBLIC_API_URL NEXT_PUBLIC_WS_URL` then `npm run build`; runner: node:22-alpine, copy `.next/standalone`, `.next/static`, `public`, `ENV HOSTNAME=0.0.0.0 PORT=3000`, non-root user).

### 7.3 `.env.example` (WP1; `.env` is a copy of it for dev)

```
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://campushire:campushire@postgres:5432/campushire
TEST_DATABASE_URL=postgresql+asyncpg://campushire:campushire@postgres:5432/campushire_test
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
JWT_SECRET=change-me-dev-only-0123456789abcdef0123456789abcdef
JWT_ACCESS_TTL_SECONDS=900
REFRESH_TTL_DAYS=7
COOKIE_SECURE=false
CORS_ORIGINS=http://localhost:3000
FRONTEND_URL=http://localhost:3000
MINIO_ENDPOINT=http://minio:9000
MINIO_PUBLIC_URL=http://localhost:9000
MINIO_ACCESS_KEY=campushire
MINIO_SECRET_KEY=campushire-secret
MINIO_REGION=us-east-1
BUCKET_RESUMES=resumes
BUCKET_DOCUMENTS=documents
BUCKET_REPORTS=reports
SMTP_HOST=mailpit
SMTP_PORT=1025
MAIL_FROM="CampusHire <no-reply@campushire.dev>"
RUN_MIGRATIONS=true
SEED_DEMO=true
RATE_LIMIT_ENABLED=true
```

For local, non-Docker backend runs, `scripts/dev.ps1 -Local` documents overrides: `localhost:5433` for Postgres, and `localhost` for Redis and MinIO.

### 7.4 Seed data (`python -m app.seed`, WP2)

The seed is idempotent: it skips if `admin@campushire.dev` exists, and wraps everything in one transaction. It writes rows directly, bypassing services, so it can create past-dated rows. It must still satisfy the DB constraints. All seeded users are email-verified. Passwords meet the policy.

| Role | Email | Password |
|---|---|---|
| ADMIN | admin@campushire.dev | Admin@12345 |
| FACULTY | faculty@campushire.dev (Dr. Ananya Rao, CSE) | Faculty@12345 |
| FACULTY | faculty2@campushire.dev (Prof. Vikram Shah, ECE) | Faculty@12345 |
| STUDENT | student@campushire.dev (Aarav Mehta, CSE, GPA 3.72) | Student@12345 |
| STUDENT | student2..student12@campushire.dev (mixed departments: CSE, ECE, ME, IT, MBA; GPA 2.6–3.95) | Student@12345 |
| COMPANY | company@campushire.dev (member of Nimbus Labs) | Company@12345 |
| (unverified demo) | pending@campushire.dev (student, unverified) | Student@12345 |

Content:
- **Companies (6, ACTIVE):**
  - Nimbus Labs, Bengaluru, `U72200KA2015PTC082345`
  - Quantix Analytics, Pune, `U74999MH2017PTC291234`
  - Orbit Robotics, Hyderabad, `U29309TG2018PTC123456`
  - GreenGrid Energy, Chennai, `L40100TN2012PLC087654`
  - Pixelcraft Studios, Remote, `US-DE5567123`
  - Finverse, Mumbai, `U67190MH2019PTC334455`
- **One PENDING company:** "Skyline Ventures", `U65999DL2021PTC377777`.
- **Internships (16), dates relative to `today`:**
  - 11 APPROVED and open (deadline +14..+40 days, start = deadline + 7..20 days, durations 8–24 weeks, stipends 0–60 000 INR, all domains covered, mixed work modes)
  - 2 PENDING_APPROVAL (one by faculty, one by company user)
  - 1 DRAFT
  - 1 CLOSED and finished (start −120 days, end −30 days), used for completed placements and feedback
  - 1 REJECTED with a reason
  - Postings are spread across faculty@, faculty2@ and company@.
- **Resumes:** one ReportLab-generated PDF per student, uploaded to bucket `resumes`, with a `documents` row. Verification statuses are mixed: mostly VERIFIED, 3 PENDING (one older than 7 days, so the compliance scan finds a violation).
- **Applications (~35):**
  - `student@` has 5: PENDING, UNDER_REVIEW, SHORTLISTED, INTERVIEW (interview at +3 days, before the deadline), and ACCEPTED on the CLOSED internship with `completed_at` set and offer details.
  - Others are distributed so every status appears, including WITHDRAWN and REJECTED.
  - Every application has a full `application_status_history`.
- **Interviews:** 4 upcoming (+2..+6 days, each before its internship deadline) and 4 past COMPLETED with results (PASS/FAIL, scores, `feedback_for_student`), plus 1 CANCELLED.
- **Evaluations:** 6, using the default form. Some have `shared_with_student=true`.
- **Feedback:**
  - 4 student_feedback on CLOSED-internship placements (spread over the past 6 months so trends render).
  - 3 company_feedback and 2 faculty_feedback.
  - 6 system_feedback (all types and statuses) with 3 action items.
- **Notifications:** 5–8 per demo user, some unread.
- **login_events:** about 400 over the last 30 days. **audit_logs:** about 60.
- **Registrations:** user `created_at` values are backdated across 90 days so the system-activity charts render.
- **Compliance:** run the compliance scan logic once at the end of the seed. It is called as a plain async function from `app.modules.admin.service` (owned by WP4). If that import fails because WP4 has not landed yet, the seed skips the step with a warning.

The README lists these credentials plus URLs:
- App: http://localhost:3000
- API docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001 (campushire / campushire-secret)
- Mailpit: http://localhost:8025

---

## 8. Work packages

### 8.0 Waves (dependency order)

```
Wave A (parallel):  WP1 Infra      WP2 Backend core       WP5 Frontend foundation
Wave B (parallel):  WP3 Backend domain   WP4 Workers/reports/admin   WP6 FE student   WP7 FE staff/admin
Wave C (serial):    WP8 Integration, tests, audit, README
```

- WP3 and WP4 start only after WP2 has delivered: models, migration, core and the module skeleton.
- WP6 and WP7 start only after WP5 has delivered: ui, shared, layout, the api layer (types + endpoints + hooks for **all** modules) and auth.
- WP3 and WP4 do not depend on each other at import time. Cross-calls go through `app.core.side_effects` and string Celery task names.

### WP1: Infrastructure and Docker

- **Owns:** `docker-compose.yml`, `.env.example`, `.env` (dev copy), `.gitattributes`, `.gitignore`, `backend/Dockerfile`, `backend/.dockerignore`, `backend/docker/entrypoint.sh`, `frontend/Dockerfile`, `frontend/.dockerignore`, `infra/**`, `scripts/*.ps1`, `README.md` (initial).
- **Deliverables:** everything in 7.1–7.3.
- `scripts/dev.ps1`:
  1. Check `docker info`. If it fails, `Start-Process "$Env:ProgramFiles\Docker\Docker\Docker Desktop.exe"` and poll `docker info` every 3 s for up to 120 s.
  2. Copy `.env.example` to `.env` if missing.
  3. Run `docker compose up -d --build`.
  4. Poll `http://localhost:8000/readyz` and `http://localhost:3000` until both are up.
- `scripts/smoke.ps1`: `Invoke-RestMethod` login for the 4 roles, `GET /auth/me`, `GET /internships` count > 0, `GET /analytics/dashboard` for each role. Exits non-zero on failure.
- **Done when:** `docker compose config` validates. With WP2/WP5 stubs, `docker compose up` starts all 7 services.

### WP2: Backend core, auth, users, models, migrations, seed

- **Owns:**
  - `backend/pyproject.toml`, `requirements*.txt`, `alembic.ini`, `alembic/**`
  - `app/main.py`, `app/api/router.py`, `app/core/**` (including `wait.py`), `app/models/__init__.py`
  - **every** `app/modules/*/models.py`
  - `app/modules/auth/**`, `app/modules/users/**`
  - `app/seed/**`
  - `tests/conftest.py`, `tests/factories.py`, `tests/test_auth.py`, `tests/test_users.py`, `tests/test_validators.py`
  - **Skeleton files (handed over):** for each of students, faculty, companies, internships, applications, interviews, evaluations, feedback, documents, notifications, reports, analytics and admin, create `__init__.py` plus `router.py` containing only `router = APIRouter(prefix="/<x>", tags=["<x>"])`. Ownership of these `router.py` files moves to WP3/WP4 once WP2 finishes. `app/api/router.py` includes them all, plus `notifications.ws` once WP4 provides it. Wrap it in `try/except ImportError` with a log warning so the app boots before WP4 exists.
- **Deliverables:**
  - All tables in section 3, exactly, with constraint names as specified.
  - Settings, async db with `get_db` (commit on success, rollback on error, then `side_effects.flush`).
  - Security (argon2, JWT, refresh rotation and reuse detection).
  - `deps.require_roles(*roles)`, `deps.current_user`, `deps.require_verified`.
  - The error envelope and IntegrityError mapping.
  - Validators:
    - `validate_email` (email-validator, `check_deliverability=False`, lowercased)
    - `normalize_phone` (strip spaces, dashes and parentheses; must match `^\+?[1-9]\d{9,14}$`; if `phonenumbers` can parse with a leading +, format E.164)
    - `validate_password`
    - `normalize_registration_number`
    - `is_pdf_magic`
  - Redis helpers, rate limiter, storage, Celery producer, side effects (`notify`, `queue_email(template, to, context)`, `queue_task(name, kwargs)`, `audit(...)`), metrics middleware (per-minute Redis hash `metrics:{yyyyMMddHHmm}` with count, errors and latency histogram buckets; TTL 2 h).
  - Auth and users endpoints.
  - The seed.
  - Verification and reset emails go through `queue_email("verify_email", ...)`. Links use `{FRONTEND_URL}/verify-email?token=...`.
- **Done when:**
  - `alembic upgrade head` runs on an empty DB.
  - `pytest tests/test_auth.py tests/test_users.py tests/test_validators.py` passes.
  - `/docs` loads.
  - Seed logins work.

### WP3: Backend domain modules

- **Owns:** for students, faculty, companies, internships, applications, interviews, evaluations, feedback and documents: `router.py`, `service.py`, `repository.py`, `schemas.py` (+ `applications/state_machine.py`). Tests: `test_students.py`, `test_companies.py`, `test_internships.py`, `test_applications.py`, `test_application_race.py`, `test_interviews.py`, `test_evaluations.py`, `test_feedback.py`, `test_documents.py`.
- **Deliverables:**
  - All endpoints in 4.4 for these modules, with role checks and ownership scoping (404 when outside scope).
  - Schemas must match section 6.
  - Every mutation calls `audit()`. Status changes and interviews call `notify()` and `queue_email()`.
  - Email templates used: `application_submitted`, `application_status`, `interview_scheduled`, `interview_rescheduled`, `interview_cancelled`, `internship_approved`, `internship_rejected`.
  - Notifications go to admins when an internship is submitted for approval.
- **Must not touch:** `models.py` and core. Put schema change needs in Requests.

### WP4: Notifications, realtime, workers, reports, analytics, admin

- **Owns:**
  - `app/modules/notifications/{router,service,repository,schemas,ws}.py`
  - `app/modules/reports/**` (except no models)
  - `app/modules/analytics/**`
  - `app/modules/admin/{router,service,repository,schemas,importer,exporter,health}.py`
  - `app/workers/**`
  - Tests: `test_notifications.py`, `test_reports.py`, `test_analytics.py`, `test_admin.py`, `test_workers.py`
- **Deliverables:**
  - The WebSocket endpoint (6.10).
  - Celery tasks, with these names:
    - `emails.send(template, to, context)` (Jinja2 HTML + text, smtplib to mailpit; interview emails attach an `.ics`)
    - `reports.export(job_id)` (builder → ReportLab PDF with title page, KPI table, charts rendered as simple ReportLab bar/pie drawings, data tables; or openpyxl XLSX with a sheet per table + KPI sheet → upload to `reports` bucket → documents row kind REPORT → job SUCCEEDED → publish `job` event + notification)
    - `data.export(job_id)`
    - `data.import(job_id)`
    - `maintenance.compliance_scan(job_id=None)`
    - `maintenance.close_expired_internships`
    - `maintenance.cleanup_tokens`
    - `maintenance.purge_pending_uploads` (PENDING_UPLOAD older than 1 h)
    - `interviews.send_reminders` (24 h before, once)
  - Beat schedule: compliance daily 02:00, close_expired hourly, cleanup daily, purge hourly, reminders every 15 min.
  - Report builders (async functions `build_<key>(session, user, params) -> ReportData`) shared by the API JSON endpoint and the worker.
  - Analytics dashboards per role.
  - Admin endpoints, including health (db `SELECT 1` timing, redis ping, minio `head_bucket` each bucket + total size via `list_objects_v2`, `celery_app.control.inspect(timeout=1).ping()`, broker queue length `LLEN celery`).
  - Import: csv/xlsx parse, per-row validation with WP3's request schemas, imported via service functions. Students get a temporary password plus an emailed reset link.
  - Report content must satisfy the table in 6.11.

### WP5: Frontend foundation

- **Owns:**
  - Frontend config files
  - `src/proxy.ts`, `src/app/layout.tsx`, `globals.css`, `page.tsx`, `not-found.tsx`, `error.tsx`
  - `src/app/(auth)/**`
  - `src/app/(app)/layout.tsx`, `(app)/dashboard`, `(app)/notifications`, `(app)/profile`, `(app)/settings`, `(app)/feedback/system`
  - `src/components/**`, `src/lib/**`, `src/providers/**`, `public/**`
- **Setup commands (in order):**
  1. `npx create-next-app@16.3.8 frontend --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --turbopack --yes`
  2. Pin `typescript@5.9.3` and `eslint@^9`.
  3. `npx shadcn@4.21.0 init -t next -b radix --no-monorepo -y`
  4. `npx shadcn@4.21.0 add <list in 5.3> -y`
  5. `npm i @tanstack/react-query @tanstack/react-query-devtools @tanstack/react-table react-hook-form @hookform/resolvers zod motion lucide-react echarts cmdk sonner next-themes date-fns`
  6. `npm i -D @playwright/test`
- **Deliverables:**
  - Design tokens (5.2), all of `components/layout`, all of `components/shared` (5.3).
  - The data layer (5.5): `types.ts` = section 6 verbatim, endpoint functions and hooks for **every** endpoint in section 4.
  - Auth pages with Zod validation (live password-strength checklist), AuthProvider, RealtimeProvider, `lib/nav.ts` for all four roles (every route in 5.1), the command palette.
  - Placeholder pages are **not** created for WP6/WP7 routes. The nav simply links to them.
- **Done when:** `npm run lint`, `npx tsc --noEmit` and `npm run build` pass, and login / register / logout work against the WP2 API.

### WP6: Frontend student experience and explorer

- **Owns:** `src/app/(app)/internships/**`, `src/app/(app)/documents/**`, `src/app/(app)/student/**`, `src/features/{student,internships,applications-wizard,documents}/**`.
- **Deliverables:** every WP6 route in 5.1 and the wizard in 5.4. Uses only the WP5 api hooks and shared components. If a hook is missing, add it locally in `src/features/<x>/api.ts` and list it in Requests.

### WP7: Frontend faculty, company and admin

- **Owns:** `src/app/(app)/{faculty,company,admin,companies}/**`, `src/features/{faculty,company,admin,review,evaluations,reports,companies}/**`.
- **Deliverables:** every WP7 route in 5.1. Company routes reuse faculty feature components with a `scope` prop.

### WP8: Integration, QA, audit (after Wave B)

- **Owns:** `tests/test_rbac_matrix.py`, `tests/test_spec_compliance.py`, `frontend/e2e/**`, final `README.md`, and it applies all Requests (it may touch any file to fix integration).
- **Deliverables:**
  1. Run the full stack and fix contract mismatches. Compare `/api/v1/openapi.json` with `types.ts` (generate `npx openapi-typescript@7 http://localhost:8000/api/v1/openapi.json -o /tmp/openapi.d.ts` and diff the key shapes).
  2. Run the complete section 9 test plan and fix failures.
  3. Fill in the spec-compliance checklist (9.5) with real file paths.
  4. Run the security checklist (9.6).
  5. Finish the README: setup, credentials, architecture diagram (ASCII), interpretation notes (interview deadline rule, registration-number formats, extensions list), troubleshooting.

---

## 9. Testing and audit plan

### 9.1 Backend test infrastructure (WP2 conftest)

- Tests run in the container: `docker compose exec api pytest -q --cov=app`. Locally: `cd backend; $env:TEST_DATABASE_URL="postgresql+asyncpg://campushire:campushire@localhost:5433/campushire_test"; python -m pytest`.
- Session fixture: drop and recreate the schema in `campushire_test` (`DROP SCHEMA public CASCADE; CREATE SCHEMA public;`), then run `alembic upgrade head` programmatically. Each test runs inside a SAVEPOINT-wrapped connection (`join_transaction_mode="create_savepoint"`) and is rolled back afterwards. **Exception:** the race test uses real separate sessions and truncates afterwards.
- Overrides:
  - `storage` → `FakeStorage` (in-memory dict; `presign_post` returns a fake ticket; tests call `fake_storage.put(key, bytes)` before `/complete`).
  - `side_effects` → a `Captured` collector (`notifications`, `emails`, `tasks` lists).
  - Redis → real redis db 15, flushed per test. Rate limiting is disabled except in `test_rate_limit`.
- Factories (`tests/factories.py`): `make_user(role, verified=True, **kw)`, `make_student`, `make_company`, `make_internship(owner, status="APPROVED", deadline_in_days=20, ...)`, `make_resume(student)`, `make_application(...)`, `auth_headers(user)`.
- Client: `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")`.

### 9.2 Required backend tests (one or more per rule)

| # | Rule (spec) | Test (file::name) |
|---|---|---|
| V1 | Email RFC 5322 | test_validators::test_email_valid_invalid (parametrised: `a@b.co` ok; `plainaddress`, `a@b`, `a..b@c.com`, `a@b..com` rejected); test_auth::test_register_invalid_email_422 |
| V1b | Email unique (case-insensitive) | test_auth::test_register_duplicate_email_409 (`Foo@x.com` vs `foo@x.com`) |
| V1c | Email verified | test_auth::test_login_unverified_403, test_auth::test_verify_email_flow, test_applications::test_apply_requires_verified |
| V2 | Phone 10–15 digits intl | test_validators::test_phone (`+919876543210` ok, `9876543210` ok, `+1 (415) 555-2671` ok → `+14155552671`, `12345` bad, `+1234567890123456` bad, letters bad); DB CHECK test inserting a raw bad phone raises IntegrityError |
| V3 | Password policy | test_validators::test_password parametrised (missing upper / lower / digit / special, length 7) |
| V4 | Resume PDF only, <= 5 MB, mandatory | test_documents::test_upload_url_rejects_non_pdf, ::test_upload_url_rejects_over_5mb (5 242 881), ::test_complete_rejects_bad_magic, ::test_complete_rejects_size_mismatch; test_applications::test_apply_without_resume_422, ::test_apply_with_foreign_resume_422; DB CHECK `ck_documents_resume_pdf` |
| V5 | Start < end, future only | test_internships::test_start_after_end_422, ::test_start_in_past_422, ::test_deadline_after_start_422, ::test_deadline_in_past_422; DB CHECK `ck_internships_dates` |
| V6 | GPA 0.0–4.0 | test_students::test_gpa_bounds (−0.1, 4.01 → 422; 0, 4.0 ok); DB CHECK |
| V7 | Status enum only | test_applications::test_invalid_status_value_422 (`"hired"`); DB CHECK `ck_applications_status` raw insert fails |
| V8 | Duration 4 weeks to 6 months | test_internships::test_duration_too_short (27 days), ::test_duration_too_long (184 days), ::test_duration_bounds_ok (28, 183), ::test_duration_weeks_mismatch_422 |
| V9 | One application per student per internship | test_applications::test_duplicate_application_409; **test_application_race::test_concurrent_duplicate_apply** (two separate AsyncClients via `asyncio.gather` → exactly one 201 and one 409, one DB row); withdrawn then reapply → 409 |
| V10 | Feedback rating int 1–5 | test_feedback::test_rating_bounds (0, 6, 3.5 → 422) for student, company and faculty feedback; DB CHECKs |
| V11 | Registration number valid + unique | test_companies::test_reg_number_formats (valid CIN, valid `US-DE5567123`, invalid `ABC`, lower case normalised), ::test_reg_number_duplicate_409 |
| V12 | Interview: not past deadline, >= 24 h notice | test_interviews::test_notice_23h59m_422, ::test_notice_24h01m_ok, ::test_after_deadline_422, ::test_reschedule_enforces_rules, ::test_requires_shortlisted, ::test_overlap_conflict_409 |
| SM | State machine | test_applications::test_transition_matrix (parametrised over all from/to pairs × role: allowed → 200 + history row, else 409), ::test_interview_create_moves_to_INTERVIEW, ::test_cancel_last_interview_back_to_SHORTLISTED, ::test_accept_requires_offer_details, ::test_withdraw_terminal |
| CRUD | Each spec CRUD bullet | students (register, read profile + history, update, deactivate → login 403), companies (create, read with ratings, update, archive, hard delete blocked when in use), internships (create, list with filters + search, update, status, archive/delete), applications (submit, read timeline, update status, withdraw), interviews (schedule, read, reschedule, result, cancel), evaluations (form CRUD, evaluate, update scores, archive/delete) |
| AUTH | Tokens | test_auth::test_refresh_rotation, ::test_refresh_reuse_revokes_family, ::test_access_expired_401_TOKEN_EXPIRED (freeze time via JWT `exp` in the past), ::test_logout_revokes, ::test_rate_limit_login_429, ::test_password_hash_is_argon2id (`$argon2id$` prefix) |
| RPT | Reports | test_reports: each report key returns 200 for the right role, 403 for the wrong role; KPI values match a small fixture dataset (e.g. placement rate 2/4 = 50.0); export job creates a PDF (`%PDF-` magic) and an XLSX (openpyxl can load it), run synchronously by calling the task function |
| NTF | Notifications | status change creates a notification row + pub/sub publish; unread count; mark read |
| ADM | Admin | health returns component statuses; import with 1 bad row reports a row error and imports the rest; compliance scan idempotent |

### 9.3 RBAC matrix test (WP8: `test_rbac_matrix.py`)

- A table-driven list of `(method, path_template, role, expected_status)` covering **every** endpoint in 4.4 for the 4 roles plus anonymous.
- Expected codes: anonymous → 401; wrong role → 403; outside-scope → 404.
- Fixture world: 2 faculty, 2 companies, 2 students, internships owned by each.
- Key cases:
  - Faculty B cannot view or modify applications for Faculty A's internship (404).
  - Student cannot PATCH application status (403).
  - Student cannot see interview `comments`.
  - Company user cannot approve internships.
  - Only admin can deactivate users or export/import.
  - Student A cannot read student B's resume URL.

### 9.4 Frontend and end-to-end

- `npm run lint`, `npx tsc --noEmit` and `npm run build` must all pass with zero errors (WP5/6/7 each run them before finishing).
- Playwright (`frontend/e2e`, WP8) against the running compose stack, `baseURL=http://localhost:3000`, chromium only:
  1. `auth.spec.ts`: login as each seeded role, land on the correct dashboard, logout; register a student shows the "check your email" state; password checklist blocks a weak password.
  2. `student-apply.spec.ts`: student2 (no application to "Frontend Engineering Intern") opens the explorer, filters domain, opens the detail page, completes the 5-step wizard uploading `e2e/fixtures/resume.pdf`, sees PENDING in My Applications. Trying again shows "already applied".
  3. `faculty-review.spec.ts`: faculty opens review, shortlists the new application, the schedule dialog rejects a time < 24 h, accepts +3 days, and the interview appears in the calendar.
  4. `admin.spec.ts`: admin approves the pending internship, opens placement-summary (the chart canvas is visible), exports PDF and the job completes.
  5. `ui.spec.ts`: Ctrl+K opens the palette; the dark-mode toggle switches the class on `<html>`.
- Compose smoke: `scripts/smoke.ps1` after `docker compose up -d --build`. Also confirm the Mailpit inbox receives a verification email on registration (`GET http://localhost:8025/api/v1/messages`).

### 9.5 Spec-compliance checklist (WP8 fills the "File(s)" column with exact paths, keeps it in README)

| # | Spec bullet | Endpoint(s) | Implementation | Test |
|---|---|---|---|---|
| C1 | Student create (email, password, name, phone, department, GPA) | POST /auth/register/student, POST /users | auth/service.py, students | test_auth |
| C2 | Student read: profile, resume, application history | GET /students/me, /students/{id}, /students/{id}/applications | students/* | test_students |
| C3 | Student update: details, resume, contact | PATCH /students/me, PUT /students/me/resume, PATCH /users/me | students/*, users/* | test_students |
| C4 | Student delete: deactivate | POST /students/{id}/deactivate, /users/{id}/deactivate | users/service.py | test_users |
| C5 | Company create (name, reg no, location, contact person) | POST /companies | companies/* | test_companies |
| C6 | Company read: details, posted internships, ratings | GET /companies/{id}, /internships, /ratings | companies/* | test_companies |
| C7 | Company update | PATCH /companies/{id} | | |
| C8 | Company archive/remove | POST /companies/{id}/archive, DELETE | | |
| C9 | Internship create (title, description, domain, duration, stipend, dates) | POST /internships | internships/* | test_internships |
| C10 | Internship read with filters and search | GET /internships, /facets | internships/repository.py (FTS + trgm) | |
| C11 | Internship update: details, status, deadline | PATCH, /submit, /approve, /reject, /close | | |
| C12 | Internship remove/archive | POST /archive, DELETE | | |
| C13 | Application create (resume, cover letter, qualifications) | POST /applications | applications/* | test_applications |
| C14 | Application read: status, timeline, feedback | GET /applications/{id} | | |
| C15 | Application update: shortlisted/accepted/rejected | PATCH /applications/{id}/status | state_machine.py | |
| C16 | Application delete: withdraw | POST /withdraw, DELETE | | |
| C17 | Interview create (date, time, interviewer) | POST /interviews | interviews/* | test_interviews |
| C18 | Interview read: schedule, results, feedback | GET /interviews | | |
| C19 | Interview update: reschedule, results, comments | PATCH /reschedule, /result | | |
| C20 | Interview cancel | POST /cancel, DELETE | | |
| C21 | Evaluation form with criteria + scoring | POST /evaluation-forms, /evaluations | evaluations/* | test_evaluations |
| C22 | Evaluation read | GET /evaluations | | |
| C23 | Evaluation update scores and feedback | PATCH /evaluations/{id} | | |
| C24 | Evaluation archive/remove | POST /archive, DELETE | | |
| V1–V12 | Data validations (each line of spec section 2) | see 9.2 | core/validators.py + DB CHECKs + lib/validation | 9.2 rows |
| R-A1..A8 | Admin: full access; manage users; approve/reject internships; view all apps; reports and analytics; compliance; export/import; system health | /users, /internships/{id}/approve, /applications, /reports, /admin/compliance, /admin/export, /admin/import, /admin/health | admin/*, reports/* | test_rbac_matrix |
| R-F1..F8 | Faculty: post; view own apps; evaluate/rate; feedback on performance; interviews; view/respond student feedback; own reports; update internship and status | POST /internships, GET /internships/{id}/applications, /evaluations, /feedback/company (as faculty) + /feedback/faculty, /interviews, /feedback/student/{id}/response, /reports (faculty keys), PATCH /internships | | test_rbac_matrix |
| R-S1..S8 | Student: browse/search; filter domain/company/location/stipend; apply with resume + cover letter; track status/timeline; upload/update resume; interview schedule + results; feedback on company/internship; rate companies + internships | GET /internships (q, domain, company_id, location, stipend_*), POST /applications, GET /applications/{id}, /documents, /interviews, POST /feedback/student (overall = internship rating, aggregated into company rating) | | test_rbac_matrix |
| RP-A1..A6 | Admin reports: placement summary, application analytics, student performance, company stats, system activity, compliance | GET /reports/{key} | reports/builders/*.py | test_reports |
| RP-F1..F4 | Faculty reports | same | | |
| RP-S1..S3 | Student reports | same | | |
| FB1 | Student post-internship feedback, 5 dimensions 1–5 + comments + trends | POST /feedback/student, GET /trends | feedback/* | test_feedback |
| FB2 | Company → student ratings (6 dimensions) + comments + hire likelihood | POST /feedback/company | | |
| FB3 | Faculty feedback (suitability, outcomes, quality, suggestions), tracked | POST /feedback/faculty | | |
| FB4 | System feedback: features, bugs, improvements; admin dashboard; action items | /feedback/system*, /feedback/action-items | | |

### 9.6 Security audit checklist (WP8 ticks each item with evidence)

- [ ] Passwords hashed with Argon2id. No password or hash in any response or log.
- [ ] JWT secret comes from env, HS256, `exp` validated, `type` claim checked (refresh tokens are never accepted as access tokens).
- [ ] Refresh tokens: opaque, stored hashed, rotated, reuse detection, revoked on logout and password reset. Cookie is HttpOnly + SameSite=Lax; `Secure` is configurable.
- [ ] CSRF guard on cookie endpoints (`X-Requested-With` + Origin check). CORS is restricted to `CORS_ORIGINS` and is not `*` with credentials.
- [ ] Every endpoint has an explicit role dependency (WP8 greps routers for routes missing `require_roles`/`current_user`, except the public allowlist). Ownership is checked in the service. Out-of-scope requests get 404.
- [ ] All SQL goes through the SQLAlchemy ORM/Core with bound params. No f-string SQL (grep `text(f"`).
- [ ] Uploads: presigned POST with content-length-range and content-type conditions, server-side HEAD size check and PDF magic check, random object keys, no user-controlled bucket, short presign TTL (upload 10 min, download 5 min). Downloads are authorised per document.
- [ ] Rate limits active on auth endpoints. Login returns a generic error message (no user enumeration). Forgot/resend always return 202.
- [ ] Import: file-size limit (5 MB), xlsx parsed with `read_only=True`, CSV formula-injection-safe on export (prefix `'` for cells starting with `= + - @`).
- [ ] Email/HTML templates use Jinja2 autoescape. The frontend never uses `dangerouslySetInnerHTML` with user content.
- [ ] Security headers: API adds `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`. Next config adds the same plus a CSP allowing `connect-src 'self' http://localhost:8000 ws://localhost:8000 http://localhost:9000` and `frame-src http://localhost:9000` (PDF viewer).
- [ ] Audit log is written for: login, user create/deactivate, internship approve/reject/archive/delete, application status change, interview create/reschedule/cancel, evaluation create/update/delete, document verification, import/export, compliance changes.
- [ ] Deactivated users: login is blocked and existing access tokens are rejected (`current_user` checks `is_active`).
- [ ] `.env` holds only dev secrets. README warns to change `JWT_SECRET` and MinIO credentials for any non-local use. `pip-audit` and `npm audit --omit=dev` have been run, and any high findings are noted.

---

## 10. Windows and dev pitfalls

1. **CRLF in shell scripts:**
   - `entrypoint.sh` with CRLF fails with `/bin/sh^M: not found`.
   - Mitigations: `.gitattributes` (`*.sh text eol=lf`), Dockerfile `sed -i 's/\r$//'`, and write files with LF.
   - Applies to any `*.sh` and `Dockerfile` heredocs.
2. **Docker daemon not running:** `docker` CLI errors with `open //./pipe/dockerDesktopLinuxEngine`. `scripts/dev.ps1` starts Docker Desktop and waits. Agents must check `docker info` before compose commands. If Docker cannot start, run the backend tests locally against a native Postgres/Redis only if available. Otherwise report it as blocked; do not fake it.
3. **Port conflicts:**
   - Host **5432 is in use** (a local Postgres), so compose maps **5433**.
   - Before `up`, check 3000/8000/6379/9000/9001/1025/8025 with `Get-NetTCPConnection -LocalPort <p> -State Listen`.
   - If one is busy, change only the host side in `docker-compose.yml` and update `.env` / NEXT_PUBLIC URLs.
4. **NEXT_PUBLIC vars baked at build:** changing the API URL requires `docker compose build frontend`.
5. **localhost inside containers is the container itself:** server-side code must use service names (`postgres`, `redis`, `minio`, `mailpit`). Only presigned URLs and browser-facing URLs use `localhost`.
6. **Bind mounts and node_modules:** we do not bind-mount source into containers. Images are self-contained, which avoids slow Windows file sharing and native-module mismatches (e.g. `lightningcss`/`@tailwindcss/oxide` built for Windows vs Linux). Never copy a Windows `node_modules` into the image: `.dockerignore` excludes `node_modules`, `.next`, `.venv`, `__pycache__`.
7. **PowerShell 5.1:** no `&&`, so use `;` with `if ($?)`. `curl` is an alias for `Invoke-WebRequest`, so use `curl.exe` or `Invoke-RestMethod`. Set `$env:VAR=...` before commands.
8. **Python venv locally:** `py -3.13 -m venv .venv; .\.venv\Scripts\Activate.ps1`. Execution policy may block it: `Set-ExecutionPolicy -Scope Process Bypass`.
9. **asyncpg on Windows host:** works, but tests must use the `WindowsSelectorEventLoopPolicy` only if psycopg is involved (it is not). Keep the default Proactor loop.
10. **Long paths:** keep the repo path short (it already is). Run `git config core.longpaths true` if git is initialised later.
11. **Timezones:** store UTC (`timestamptz`), compute "now" with `datetime.now(UTC)`. The frontend displays in the browser's local zone with date-fns. The 24 h rule is compared in UTC on the server.
12. **MinIO image:** do not use `minio/minio` or `minio/mc` (unpublished since Oct 2025). Use the pinned `pgsty/minio` tag.
13. **Volumes:** `docker compose down -v` wipes data. The seed re-runs automatically on the next `up` because `SEED_DEMO=true` and the seed is idempotent.

---

## 11. Definition of done (whole project)

- [ ] `scripts/dev.ps1` brings up all 7 services from scratch. `scripts/smoke.ps1` passes.
- [ ] All four seeded roles can log in at http://localhost:3000 and land on populated dashboards.
- [ ] Backend `pytest` is green (all section 9.2 rows), with coverage >= 75% on `app/modules`.
- [ ] Frontend lint, typecheck and build are green. The 5 Playwright specs are green.
- [ ] The spec-compliance table (9.5) has every row filled with a file path and a passing test.
- [ ] Every security checklist item (9.6) is ticked.
- [ ] README covers: setup (Windows), credentials, URLs, architecture, extensions list, interpretation notes, troubleshooting.
