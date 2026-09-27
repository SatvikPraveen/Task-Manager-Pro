"""
storage/database.py

SQLAlchemy engine, session factory and declarative base.

The engine is built from :func:`task_manager_pro.config.get_settings`. SQLite
URLs get the connection arguments they need for multi-threaded ASGI servers,
and the special ``sqlite:///:memory:`` URL is backed by a ``StaticPool`` so
that every session shares the same in-memory database (otherwise each new
connection would see an empty schema).
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from task_manager_pro.config import get_settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def make_engine(database_url: Optional[str] = None, *, echo: Optional[bool] = None) -> Engine:
    """
    Build an engine for ``database_url`` (defaults to the configured URL).

    SQLite gets ``check_same_thread=False`` because FastAPI may service a
    request on a different thread than the one that opened the connection, and
    foreign-key enforcement is switched on per connection (SQLite defaults it
    to off, which would silently break the ``tasks.user_id`` constraint).
    """
    settings = get_settings()
    url = database_url or settings.database_url
    echo_sql = settings.sql_echo if echo is None else echo

    kwargs: dict = {"echo": echo_sql}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url.endswith(":memory:"):
            kwargs["poolclass"] = StaticPool
    else:
        # Detect stale connections (e.g. after a DB restart) before use.
        kwargs["pool_pre_ping"] = True

    new_engine = create_engine(url, **kwargs)

    if url.startswith("sqlite"):

        @event.listens_for(new_engine, "connect")
        def _enable_sqlite_fks(dbapi_connection, _record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return new_engine


engine: Engine = make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI-style dependency yielding a session that is always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(bind: Optional[Engine] = None) -> None:
    """Create all tables. Idempotent; used for dev/test bootstrapping.

    Production deployments should run ``alembic upgrade head`` instead so that
    schema changes are versioned.
    """
    Base.metadata.create_all(bind=bind or engine)
