"""
core/database.py
SQLAlchemy engine, session factory, and get_db dependency.

Uses SQLite by default (zero-install, file-based).
Override DATABASE_URL env var for PostgreSQL in production:
  DATABASE_URL=postgresql+psycopg2://user:pass@host/db
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shopfloor.db")

# connect_args is SQLite-specific — prevents thread-safety errors in FastAPI
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    echo=False,          # Set True to log all SQL for debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and closes it on teardown."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables if they don't exist (used on startup)."""
    # Import here to ensure all models are registered with Base
    import core.models_db  # noqa: F401
    Base.metadata.create_all(bind=engine)
