#!/bin/sh
# CampusHire container entrypoint: wait for deps, migrate, ensure buckets, seed, exec CMD.
set -e

echo "[entrypoint] waiting for postgres, redis and minio..."
python -m app.core.wait

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "[entrypoint] alembic upgrade head"
  alembic upgrade head
fi

echo "[entrypoint] ensuring buckets"
python -c "from app.core.storage import ensure_buckets; ensure_buckets()"

if [ "${SEED_DEMO:-false}" = "true" ]; then
  echo "[entrypoint] seeding demo data (idempotent)"
  python -m app.seed
fi

echo "[entrypoint] starting: $*"
exec "$@"
