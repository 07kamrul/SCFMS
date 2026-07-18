"""Synchronous SQLAlchemy engine and session factory.

We use sync sessions with FastAPI's threadpool (endpoints declared as `def`).
This keeps PostGIS/GeoAlchemy2 usage simple and avoids async driver pitfalls
for the spatial workloads that dominate this app.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a session and guaranteeing cleanup.

    Commits are the caller's (service layer's) responsibility; this only
    rolls back on error and always closes.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
