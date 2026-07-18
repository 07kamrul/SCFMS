"""Generic repository base.

Encapsulates data access so services depend on an interface, not on SQLAlchemy
query construction. All tenant-scoped queries MUST pass company_id.
"""
from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: Session):
        self.db = db

    def get(self, id_: uuid.UUID) -> ModelT | None:
        return self.db.get(self.model, id_)

    def get_for_company(self, id_: uuid.UUID, company_id: uuid.UUID) -> ModelT | None:
        """Fetch by id but only if it belongs to the given company (tenant guard)."""
        stmt = select(self.model).where(
            self.model.id == id_,  # type: ignore[attr-defined]
            self.model.company_id == company_id,  # type: ignore[attr-defined]
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def add(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        self.db.flush()
        return obj

    def delete(self, obj: ModelT) -> None:
        self.db.delete(obj)
        self.db.flush()

    def count_for_company(self, company_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(self.model).where(
            self.model.company_id == company_id  # type: ignore[attr-defined]
        )
        return int(self.db.execute(stmt).scalar_one())
