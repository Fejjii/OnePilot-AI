from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from onepilot.core.config import get_settings

_engine = None
SessionLocal: sessionmaker[Session] = sessionmaker()


def get_engine():  # type: ignore[no-untyped-def]
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {}
        if settings.DATABASE_URL.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.is_dev,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        SessionLocal.configure(bind=_engine)
    return _engine


def init_db() -> None:
    get_engine()


def get_session() -> Generator[Session, None, None]:
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
