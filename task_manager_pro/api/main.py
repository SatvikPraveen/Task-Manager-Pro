"""
api/main.py

FastAPI application factory and ASGI entry point.

Middleware stack (outermost first):

    RequestIdMiddleware      correlation ID, timing headers, access log, JSON 500s
    SecurityHeadersMiddleware
    MetricsMiddleware        Prometheus count/latency per route template
    RateLimitMiddleware      sliding window on /api/auth/{login,register}
    CORSMiddleware
    → routers
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from task_manager_pro.api.middleware import (
    RateLimitMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
    SlidingWindowRateLimiter,
)
from task_manager_pro.api.routes import auth, tasks, users
from task_manager_pro.config import Settings, get_settings
from task_manager_pro.observability.logging import configure_logging
from task_manager_pro.observability.metrics import MetricsMiddleware, metrics_endpoint
from task_manager_pro.storage.database import engine, init_db

logger = logging.getLogger(__name__)

try:
    API_VERSION = _pkg_version("task-manager-pro")
except PackageNotFoundError:  # running from a source checkout without `pip install -e .`
    API_VERSION = "0.0.0+unknown"

RATE_LIMITED_PATHS = ("/api/auth/login", "/api/auth/register")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create tables on startup (dev convenience; production uses Alembic)."""
    init_db()
    logger.info("Database initialised", extra={"database": get_settings().database_url.split("@")[-1]})
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a fully wired application. Tests may pass custom settings."""
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_json)

    app = FastAPI(
        title=settings.app_name,
        description="Task management API with JWT auth, SQL-side querying, rate limiting and Prometheus metrics.",
        version=API_VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Innermost first (add_middleware wraps the existing stack each time).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            limiter=SlidingWindowRateLimiter(settings.auth_rate_limit_per_minute, 60.0),
            paths=RATE_LIMITED_PATHS,
        )
    if settings.metrics_enabled:
        app.add_middleware(MetricsMiddleware)
        app.add_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)

    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
    app.include_router(users.router, prefix="/api/users", tags=["Users"])

    @app.get("/", tags=["Meta"])
    async def root() -> dict[str, str]:
        """API information."""
        return {
            "message": "🎯 Task Manager PRO API",
            "version": API_VERSION,
            "docs": "/api/docs",
            "openapi_schema": "/api/openapi.json",
        }

    @app.get("/health", tags=["Meta"])
    async def health_check() -> JSONResponse:
        """Liveness + readiness: verifies the database answers a trivial query."""
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "ok"
            status_code = 200
        except Exception as exc:  # pragma: no cover - exercised only with a broken DB
            logger.error("Health check database probe failed: %s", exc)
            db_status = "unavailable"
            status_code = 503
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "healthy" if status_code == 200 else "degraded",
                "version": API_VERSION,
                "database": db_status,
            },
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    _settings = get_settings()
    uvicorn.run(
        "task_manager_pro.api.main:app",
        host=_settings.host,
        port=_settings.port,
        reload=_settings.environment == "development",
    )
