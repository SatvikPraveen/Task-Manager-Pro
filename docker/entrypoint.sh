#!/usr/bin/env sh
# Container entrypoint.
#   serve            → alembic upgrade head, then uvicorn (default)
#   migrate          → alembic upgrade head only
#   anything else    → executed verbatim (e.g. `task-manager --help`)
set -eu

case "${1:-serve}" in
  serve)
    echo "Applying database migrations..."
    alembic upgrade head
    echo "Starting API on ${HOST:-0.0.0.0}:${PORT:-8000}"
    exec uvicorn task_manager_pro.api.main:app \
      --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" \
      --workers "${WEB_CONCURRENCY:-1}" --proxy-headers --forwarded-allow-ips="*"
    ;;
  migrate)
    exec alembic upgrade head
    ;;
  *)
    exec "$@"
    ;;
esac
