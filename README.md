# 📝 Task Manager PRO

[![CI/CD](https://github.com/SatvikPraveen/Task-Manager-Pro/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/SatvikPraveen/Task-Manager-Pro/actions/workflows/ci-cd.yml)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-darkgreen.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-red.svg)](https://www.sqlalchemy.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A task-management **REST API + CLI** in Python that is built the way a
production service is: one validated configuration source, SQL-side querying
with an injectable repository, JWT auth hardened against enumeration and
brute force, request correlation, structured logs, Prometheus metrics,
versioned migrations, and a **property-tested urgency model** that answers
"what should I do next?".

---

## ✨ Highlights

| Area | What you get |
|---|---|
| **API** | 20 endpoints: auth (register/login/refresh), task CRUD with filtering, sorting and pagination in SQL, `stats` and `next` analytics, profile management |
| **Ranking** | `GET /api/tasks/next` orders pending tasks by a bounded logistic urgency score `w·σ((d₀−d)/τ)` — priority-weighted, monotone in deadline, saturating for overdue tasks ([ADR-0003](docs/adr/0003-bounded-logistic-urgency.md)) |
| **Analytics** | `GET /api/tasks/stats`: completion & on-time rates, overdue load, mean/median completion latency, per-priority breakdown |
| **Security** | bcrypt (cost 12), JWT with `iat`/`jti`/`type`, constant-time login, sliding-window rate limit on auth endpoints, security headers, ownership enforced in SQL ([SECURITY.md](SECURITY.md)) |
| **Observability** | `X-Request-ID` / `X-Process-Time` on every response, JSON logs with request IDs, `/metrics` (Prometheus, labelled by route template), `/health` with a DB probe |
| **Persistence** | SQLAlchemy 2.0, SQLite or PostgreSQL, Alembic migrations with a drift check in CI, composite index on the hot query |
| **Quality** | 76 tests incl. Hypothesis property tests, 80 % coverage gate, Ruff, mypy (pydantic plugin), Bandit, pip-audit, pre-commit; CI matrix 3.10–3.13 × SQLite + 3.12 × PostgreSQL 16 |
| **Ops** | Multi-stage non-root Docker image (migrates then serves), `docker compose` with PostgreSQL + Prometheus, `Makefile`, benchmark and seed scripts |

---

## 🚀 Quick start

```bash
git clone https://github.com/SatvikPraveen/Task-Manager-Pro.git && cd Task-Manager-Pro
python -m venv .venv && source .venv/bin/activate
make install                       # pip install -e ".[dev,postgres]" + pre-commit hooks

cp .env.template .env
python -c 'import secrets; print(secrets.token_hex(32))'   # paste as SECRET_KEY in .env

make migrate                       # alembic upgrade head  (SQLite by default)
make run                           # http://127.0.0.1:8000/api/docs
```

Try it:

```bash
curl -s -X POST localhost:8000/api/auth/register -H 'content-type: application/json' \
  -d '{"username":"alice","password":"correct-horse-battery","email":"alice@example.com"}'

TOKEN=$(curl -s -X POST localhost:8000/api/auth/login -H 'content-type: application/json' \
  -d '{"username":"alice","password":"correct-horse-battery"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s -X POST localhost:8000/api/tasks -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"title":"Write paper","due_date":"2026-10-01","priority":"high"}'

curl -s "localhost:8000/api/tasks?priority=high&sort_by=due_date&limit=5" -H "authorization: Bearer $TOKEN"
curl -s localhost:8000/api/tasks/next -H "authorization: Bearer $TOKEN"
curl -s localhost:8000/api/tasks/stats -H "authorization: Bearer $TOKEN"
```

Or the whole stack with PostgreSQL and Prometheus:

```bash
docker compose up --build        # API on :8000, Prometheus on :9090
```

---

## 📚 API overview

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/auth/register` | Create an account (rate-limited) |
| `POST` | `/api/auth/login` | Get a bearer token (`expires_in` included; rate-limited; constant-time) |
| `POST` | `/api/auth/refresh-token` | New token for a valid bearer |
| `GET` | `/api/tasks` | List with `completed`, `priority`, `due_before`, `due_after`, `q`, `sort_by`, `sort_desc`, `skip`, `limit` |
| `POST` | `/api/tasks` | Create |
| `GET` | `/api/tasks/next?limit=5` | Most urgent pending tasks with `urgency` and `days_until_due` |
| `GET` | `/api/tasks/stats` | Workload statistics |
| `GET` / `PUT` / `DELETE` | `/api/tasks/{id}` | Read / partial update / delete (404 for other users' tasks) |
| `GET` / `PUT` | `/api/users/me` | Profile |
| `POST` | `/api/users/me/toggle-reminders` | Flip email reminders |
| `GET` | `/health`, `/metrics`, `/` | Readiness (DB probe), Prometheus, info |

Interactive docs: `/api/docs` (Swagger) and `/api/redoc`. OpenAPI: `/api/openapi.json`.

---

## 🧠 The urgency model in one paragraph

For a pending task with priority weight `w ∈ {1, 2, 3}` and `d` fractional
days until its due date (negative when overdue),
`U = w · σ((d₀ − d) / τ)` with `d₀ = 3`, `τ = 2` and `σ` the logistic
function. `U` is bounded by `w` (a low-priority task never outranks a
high-priority one that is at least as close), strictly decreasing in `d`,
monotone in priority, zero for completed tasks, and the ranking breaks ties
on due date then ID. These are not just claims: `tests/test_analytics.py`
checks them with Hypothesis across thousands of generated dates,
priorities and parameter settings.

---

## 🛠️ Development

```bash
make lint          # ruff check + ruff format --check
make typecheck     # mypy (pydantic plugin, strict on new packages)
make security      # bandit
make audit         # pip-audit
make test          # pytest with the 80 % coverage gate
make migrate-check # alembic upgrade head && alembic check
make seed          # deterministic demo data (scripts/seed_data.py --seed 42)
make bench         # benchmarks/bench_api.py against BASE_URL
```

Configuration is documented in [`.env.template`](.env.template) and
validated at startup by [`task_manager_pro/config.py`](task_manager_pro/config.py).

### Project layout

```
task_manager_pro/
├── config.py               # Settings (pydantic-settings), the only config source
├── api/
│   ├── main.py             # create_app(): middleware stack + routers
│   ├── dependencies.py     # bearer auth, repository provider
│   ├── middleware/         # request_id, security_headers, rate_limit
│   └── routes/             # auth, tasks (+stats, +next), users
├── analytics/              # urgency model + statistics (pure, property-tested)
├── observability/          # structured logging, Prometheus metrics
├── storage/                # engine/session, ORM models, SQLStorage repository
├── schemas/                # Pydantic v2 request/response models
├── utils/                  # bcrypt/JWT, SMTP, CLI helpers
├── services/, models/, cli.py, send_reminders.py   # original JSON-backed CLI
migrations/                 # Alembic environment + revisions
tests/                      # 76 tests (unit, property-based, API integration)
benchmarks/, scripts/       # bench_api.py, seed_data.py
docs/                       # ARCHITECTURE.md, adr/, phase write-ups
```

---

## 📖 Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — components, request lifecycle, data model, testing strategy, operations
- [docs/adr/](docs/adr/README.md) — architecture decision records
- [SECURITY.md](SECURITY.md) — threat controls and reporting
- [CHANGELOG.md](CHANGELOG.md) — release notes
- [migrations/README.md](migrations/README.md) — working with Alembic
- Phase write-ups: [Database & security](docs/PHASE2_DATABASE_SECURITY.md), [REST API](docs/PHASE3_REST_API.md), [Testing & CI/CD](docs/PHASE4_TESTING_CI_CD.md)

## 💻 CLI

The original JSON-backed CLI is still available:

```bash
pip install -e .
task-manager login --username alice
task-manager add-task --title "My Task" --desc "…" --due 2026-12-31
task-manager list-tasks --filter pending --summary
```

## 🤝 Contributing & license

See [CONTRIBUTING.md](CONTRIBUTING.md). Licensed under the
[GPL-3.0](LICENSE). If this project is useful in your work, please cite it
([CITATION.cff](CITATION.cff)).
