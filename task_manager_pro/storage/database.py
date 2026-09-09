"""
storage/database.py

Database configuration and session management for SQLAlchemy ORM.
Provides database engine, session factory, and Base class for all models.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

# Database URL (defaults to SQLite in project root)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",  # Set SQL_ECHO=true for debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for model definitions
class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection function to provide a database session.
    Used with FastAPI and other frameworks.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize the database by creating all tables defined in models.
    Should be called once at application startup.
    """
    Base.metadata.create_all(bind=engine)
