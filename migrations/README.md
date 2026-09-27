# Database migrations

Schema changes are versioned with [Alembic](https://alembic.sqlalchemy.org/).
`migrations/env.py` reads `DATABASE_URL` from the application settings, so the
same commands work for SQLite in development and PostgreSQL in production.

```bash
# Apply every pending migration
alembic upgrade head

# Generate a migration after editing task_manager_pro/storage/models.py
alembic revision --autogenerate -m "add tags to tasks"

# Verify that the models and the migration history agree (CI runs this)
alembic check

# Roll back one step
alembic downgrade -1
```

`init_db()` (used by the API's startup hook and the tests) still creates
tables directly from the models for convenience. Production deployments
should run `alembic upgrade head` before starting the server and set nothing
else; the two approaches produce identical schemas, which `alembic check`
enforces.
