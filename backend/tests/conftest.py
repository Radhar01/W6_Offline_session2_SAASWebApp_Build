"""Shared pytest fixtures for the ClipCreator backend test suite.

Uses an in-memory SQLite database (shared across connections via
`StaticPool`) instead of the real PostgreSQL instance, so the suite runs
without any live database. All SQLAlchemy column types used by the
`Video`/`Clip` models (Integer, Float, String, Enum, DateTime) are
SQLite-compatible.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models.base import Base

# A single shared in-memory SQLite database for the whole test process.
# `StaticPool` ensures every connection (including ones opened by background
# tasks via `TestSessionLocal`) sees the same in-memory database rather than
# each getting its own empty one.
TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Create all tables, yield a session, then drop all tables."""
    Base.metadata.create_all(bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """A FastAPI TestClient whose `get_db` dependency yields `db_session`.

    Also points `app.routers.clip_generation.SessionLocal` (used directly by
    the background clip-generation worker, bypassing the `get_db` dependency
    override) at the same test-backed session factory, so background tasks
    triggered during a test read/write the same SQLite database.
    """

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    import app.routers.clip_generation as clip_generation_module

    original_session_local = clip_generation_module.SessionLocal
    clip_generation_module.SessionLocal = TestSessionLocal

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    clip_generation_module.SessionLocal = original_session_local
