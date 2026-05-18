from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import DateTime, String, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

T = TypeVar("T", bound="Base")


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class TenantMixin:
    organization_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)


class BaseRepository(Generic[T]):
    """Generic repository enforcing tenant isolation on all reads."""

    def __init__(self, session: Session, model_class: type[T]) -> None:
        self._session = session
        self._model = model_class

    def get(self, id: str, *, organization_id: str | None = None) -> T | None:
        stmt = select(self._model).where(self._model.id == id)  # type: ignore[attr-defined]
        if organization_id and hasattr(self._model, "organization_id"):
            stmt = stmt.where(self._model.organization_id == organization_id)  # type: ignore[attr-defined]
        return self._session.execute(stmt).scalar_one_or_none()

    def list_all(
        self,
        *,
        organization_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[T]:
        stmt = select(self._model)
        if organization_id and hasattr(self._model, "organization_id"):
            stmt = stmt.where(self._model.organization_id == organization_id)  # type: ignore[attr-defined]
        stmt = stmt.offset(offset).limit(limit)
        return list(self._session.execute(stmt).scalars().all())

    def count(self, *, organization_id: str | None = None) -> int:
        stmt = select(func.count()).select_from(self._model)
        if organization_id and hasattr(self._model, "organization_id"):
            stmt = stmt.where(self._model.organization_id == organization_id)  # type: ignore[attr-defined]
        result = self._session.execute(stmt).scalar()
        return result or 0

    def create(self, obj: T) -> T:
        self._session.add(obj)
        self._session.flush()
        return obj

    def update(self, obj: T, data: dict[str, Any]) -> T:
        for key, value in data.items():
            setattr(obj, key, value)
        self._session.flush()
        return obj

    def delete(self, obj: T) -> None:
        self._session.delete(obj)
        self._session.flush()
