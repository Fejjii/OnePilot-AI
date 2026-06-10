from __future__ import annotations

import os
from collections.abc import Generator

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"
os.environ["DEV_AUTH_ENABLED"] = "false"
os.environ["DEV_BYPASS_QUOTAS"] = "false"
os.environ["QDRANT_URL"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["SERPER_API_KEY"] = ""
os.environ["REDIS_URL"] = ""
os.environ["GOOGLE_CLIENT_ID"] = ""
os.environ["GOOGLE_CLIENT_SECRET"] = ""
os.environ["GOOGLE_REFRESH_TOKEN"] = ""
os.environ["GMAIL_PROVIDER_MODE"] = "auto"
os.environ["GOOGLE_CALENDAR_PROVIDER_MODE"] = "auto"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from onepilot.api.main import create_app  # noqa: E402
from onepilot.core.config import get_settings  # noqa: E402
from onepilot.providers import reset_provider_cache  # noqa: E402
from onepilot.security.rate_limit import reset_rate_limiter  # noqa: E402
from onepilot.repositories.base import Base  # noqa: E402
from onepilot.repositories.models import Plan  # noqa: E402
from onepilot.repositories.session import get_session  # noqa: E402

PLAN_SEEDS = [
    {
        "code": "free",
        "name": "Free",
        "monthly_price_cents": 0,
        "limits": {
            "chat_messages": 50,
            "rag_queries": 20,
            "document_uploads": 5,
            "storage_mb": 100,
            "email_drafts": 10,
            "lead_workflows": 5,
            "tool_calls": 30,
            "users": 1,
        },
    },
    {
        "code": "pro",
        "name": "Pro",
        "monthly_price_cents": 2900,
        "limits": {
            "chat_messages": 500,
            "rag_queries": 200,
            "document_uploads": 50,
            "storage_mb": 1000,
            "email_drafts": 100,
            "lead_workflows": 50,
            "tool_calls": 300,
            "users": 1,
        },
    },
    {
        "code": "team",
        "name": "Team",
        "monthly_price_cents": 7900,
        "limits": {
            "chat_messages": 2000,
            "rag_queries": 1000,
            "document_uploads": 200,
            "storage_mb": 5000,
            "email_drafts": 500,
            "lead_workflows": 200,
            "tool_calls": 1000,
            "users": 10,
        },
    },
    {
        "code": "business",
        "name": "Business",
        "monthly_price_cents": 19900,
        "limits": {
            "chat_messages": 10000,
            "rag_queries": 5000,
            "document_uploads": 1000,
            "storage_mb": 25000,
            "email_drafts": 2000,
            "lead_workflows": 1000,
            "tool_calls": 5000,
            "users": 50,
        },
    },
]


@pytest.fixture(scope="session")
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    Base.metadata.create_all(eng)

    _session = sessionmaker(bind=eng)()
    for p in PLAN_SEEDS:
        _session.merge(Plan(**p))
    _session.commit()
    _session.close()

    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db_session(engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def _reset_providers():
    get_settings.cache_clear()
    reset_provider_cache()
    reset_rate_limiter()
    yield
    get_settings.cache_clear()
    reset_provider_cache()
    reset_rate_limiter()


@pytest.fixture
def app(engine):
    return create_app()


@pytest.fixture
def client(app, engine) -> Generator[TestClient, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    def _override_get_session():
        yield session

    app.dependency_overrides[get_session] = _override_get_session
    with TestClient(app) as tc:
        yield tc
    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_session(app, engine):
    """Yield (TestClient, Session) where the session is the same one the app uses."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    def _override_get_session():
        yield session

    app.dependency_overrides[get_session] = _override_get_session
    with TestClient(app) as tc:
        yield tc, session
    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()
