# Quick Start – Task Manager PRO API

## 1. Install and configure

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,postgres,redis]"        # or: make install

cp .env.template .env
python -c 'import secrets; print(secrets.token_hex(32))'   # paste as SECRET_KEY in .env
```

Every setting is documented in `.env.template` and validated at startup; an
invalid value fails immediately with a precise message.

## 2. Migrate and run

```bash
alembic upgrade head                                   # or: make migrate
uvicorn task_manager_pro.api.main:app --reload         # or: make run
```

- Swagger UI: http://127.0.0.1:8000/api/docs
- ReDoc: http://127.0.0.1:8000/api/redoc
- Health (with DB probe): http://127.0.0.1:8000/health
- Prometheus metrics: http://127.0.0.1:8000/metrics

Or the full stack (PostgreSQL + Redis + Prometheus):

```bash
docker compose up --build
```

## 3. Use the API

```bash
BASE=http://127.0.0.1:8000

# Register and log in
curl -s -X POST $BASE/api/auth/register -H 'content-type: application/json' \
  -d '{"username":"alice","password":"correct-horse-battery","email":"alice@example.com"}'
TOKEN=$(curl -s -X POST $BASE/api/auth/login -H 'content-type: application/json' \
  -d '{"username":"alice","password":"correct-horse-battery"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
AUTH="authorization: Bearer $TOKEN"

# Create tasks
curl -s -X POST $BASE/api/tasks -H "$AUTH" -H 'content-type: application/json' \
  -d '{"title":"Write paper","due_date":"2026-10-01","priority":"high","description":"draft intro"}'

# List: filter, search, sort, paginate — all in SQL
curl -s "$BASE/api/tasks?completed=false&priority=high&q=paper&sort_by=due_date&limit=10" -H "$AUTH"

# What should I do next?  (add &calibrated=true to fit the curve to your history)
curl -s "$BASE/api/tasks/next?limit=5" -H "$AUTH"

# Workload statistics
curl -s $BASE/api/tasks/stats -H "$AUTH"

# Update / complete / delete
curl -s -X PUT $BASE/api/tasks/<id> -H "$AUTH" -H 'content-type: application/json' -d '{"completed":true}'
curl -s -X DELETE $BASE/api/tasks/<id> -H "$AUTH"

# Rotate the token (old one is revoked), or log out (revokes it immediately)
curl -s -X POST $BASE/api/auth/refresh-token -H "$AUTH"
curl -s -X POST $BASE/api/auth/logout -H "$AUTH"
```

Every response carries `X-Request-ID`; quote it when reporting a problem.

## 4. Run the checks

```bash
make lint typecheck security test      # what CI runs
make migrate-check                     # models ⇔ migrations
make seed                              # deterministic demo data
make bench                             # latency percentiles against a running server
```

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `SECRET_KEY must be at least 32 characters` | Generate one: `openssl rand -hex 32` |
| `401 Token has been revoked` | You logged out or refreshed; log in again |
| `429 Too many requests` | Auth endpoints are rate-limited (`AUTH_RATE_LIMIT_PER_MINUTE`); wait for `Retry-After` |
| `503` from `/health` | Database unreachable; check `DATABASE_URL` |
| `SHARED_STATE_BACKEND=redis requires REDIS_URL` | Set `REDIS_URL` or switch back to `memory` |
| Address already in use | `uvicorn ... --port 8001` |

More: [README](README.md) · [Architecture](docs/ARCHITECTURE.md) · [ADRs](docs/adr/README.md) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md)
