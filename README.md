# CampusHire

College internship and talent management platform: students browse and apply to internships, faculty and companies review applications and run interviews, admins approve postings, run reports and manage the system. See `PLAN.md` for the full design. Features marked **[EXT]** are extensions beyond the assignment spec.

> This README is the initial infrastructure version (WP1). WP8 finalises it with architecture, extensions list, interpretation notes and the spec-compliance table.

## Quick start (Windows, Docker Desktop)

Requirements: Docker Desktop (WSL2 backend), PowerShell 5.1+.

```powershell
.\scripts\dev.ps1      # starts Docker Desktop if needed, creates .env, builds, brings everything up, waits for health
.\scripts\smoke.ps1    # health checks + login as each seeded role
.\scripts\test.ps1     # backend pytest (in the api container) + frontend lint/typecheck/build
.\scripts\reset.ps1    # wipe all data (down -v) and start fresh; the demo seed re-runs automatically
```

If PowerShell blocks scripts: `Set-ExecutionPolicy -Scope Process Bypass`.
First start builds three images and runs migrations plus the seed, so give it a few minutes.

## URLs

| What | URL |
|---|---|
| App | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| MinIO console | http://localhost:9001 (campushire / campushire-secret) |
| Mailpit (all outgoing email) | http://localhost:8025 |
| Postgres (host access) | `localhost:5433`, user/password/db `campushire` (test DB: `campushire_test`) |

## Demo credentials (seeded)

| Role | Email | Password |
|---|---|---|
| Admin | admin@campushire.dev | Admin@12345 |
| Faculty | faculty@campushire.dev, faculty2@campushire.dev | Faculty@12345 |
| Student | student@campushire.dev, student2..student12@campushire.dev | Student@12345 |
| Company | company@campushire.dev | Company@12345 |
| Unverified student | pending@campushire.dev | Student@12345 |

## Services (docker-compose.yml)

| Service | Image | Host port | Notes |
|---|---|---|---|
| frontend | built from `frontend/` (Next.js standalone) | 3000 | `NEXT_PUBLIC_*` are build args |
| api | built from `backend/` (FastAPI) | 8000 | entrypoint waits for deps, migrates, creates buckets, seeds |
| worker | same image as api | none | Celery worker with embedded beat (`-B`) |
| postgres | postgres:17-alpine | 5433 | volume `pgdata`; init script creates `campushire_test` |
| redis | redis:7.4-alpine | 6379 | volume `redisdata` |
| minio | pgsty/minio (community fork) | 9000, 9001 | volume `miniodata` |
| mailpit | axllent/mailpit:v1 | 1025 (SMTP), 8025 (UI) | |

Common commands:

```powershell
docker compose ps
docker compose logs -f api worker
docker compose exec api pytest -q --cov=app
docker compose build frontend      # needed after changing NEXT_PUBLIC_* values
docker compose down                # stop, keep data
```

## Configuration

Copy `.env.example` to `.env` (`dev.ps1` does this automatically). All values are development-only.

> **Warning:** change `JWT_SECRET` and the MinIO credentials (`MINIO_*`, and `MINIO_ROOT_*` in `docker-compose.yml`) before any non-local use.

## Troubleshooting

- **Docker daemon not running** (`open //./pipe/dockerDesktopLinuxEngine`): run `.\scripts\dev.ps1`, it starts Docker Desktop and waits.
- **Port already in use:** the stack needs 3000, 8000, 5433, 6379, 9000, 9001, 1025, 8025. Host Postgres on 5432 is why Postgres is mapped to 5433. To move a port, change only the host side in `docker-compose.yml` (and `.env` / `NEXT_PUBLIC_*` URLs if it is 3000 or 8000).
- **`/bin/sh^M: not found` from the api container:** `backend/docker/entrypoint.sh` must have LF endings. `.gitattributes` enforces this and the Dockerfile also strips CR.
- **Frontend still calls the old API URL:** `NEXT_PUBLIC_*` is inlined at build time; run `docker compose build frontend`.
- **Fresh data:** `.\scripts\reset.ps1`.
- **Backend outside Docker:** `.\scripts\dev.ps1 -Local` prints the env overrides (Postgres on `localhost:5433`, Redis/MinIO on `localhost`).
