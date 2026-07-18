"""Pytest fixtures.

Tests require a PostgreSQL database (the models use PG-specific types: UUID,
JSONB, ENUM). Point TEST_DATABASE_URL at a disposable database; the schema is
created via metadata.create_all and dropped at the end of the session.

    export TEST_DATABASE_URL="postgresql+psycopg://scfms:scfms@localhost:5432/scfms_test"
"""
from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_current_user  # noqa: F401  (imported for clarity)
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Company, CompanySettings, User  # noqa: F401 register models

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://scfms:scfms_dev_password@localhost:5432/scfms_test",
)

engine = create_engine(TEST_DATABASE_URL, poolclass=None, future=True)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    # Milestone 1 tables use no geometry. Enable PostGIS if available (needed by
    # later milestones) but don't fail the suite if the extension isn't installed.
    with engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            conn.commit()
        except Exception:
            conn.rollback()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db() -> Iterator[Session]:
    """A session wrapped in a transaction rolled back after each test."""
    connection = engine.connect()
    trans = connection.begin()
    # create_savepoint makes service-layer commit()s release a SAVEPOINT rather
    # than the outer transaction, so trans.rollback() fully isolates each test.
    session = TestingSessionLocal(
        bind=connection, join_transaction_mode="create_savepoint"
    )
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    def _override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
