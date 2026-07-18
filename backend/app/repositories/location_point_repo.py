"""LocationPoint data access — append-only GPS log, always tenant-scoped."""
from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import delete, select

from app.models.location_point import LocationPoint
from app.repositories.base import BaseRepository


class LocationPointRepository(BaseRepository[LocationPoint]):
    model = LocationPoint

    def get_latest_for_user(
        self, *, company_id: uuid.UUID, user_id: uuid.UUID
    ) -> LocationPoint | None:
        stmt = (
            select(LocationPoint)
            .where(LocationPoint.company_id == company_id, LocationPoint.user_id == user_id)
            .order_by(LocationPoint.recorded_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_latest_for_users(
        self, *, company_id: uuid.UUID, user_ids: Iterable[uuid.UUID]
    ) -> dict[uuid.UUID, LocationPoint]:
        """One query for many users via DISTINCT ON (user_id) — avoids an N+1
        when building the team tracking map."""
        user_ids = list(user_ids)
        if not user_ids:
            return {}
        stmt = (
            select(LocationPoint)
            .where(LocationPoint.company_id == company_id, LocationPoint.user_id.in_(user_ids))
            .distinct(LocationPoint.user_id)
            .order_by(LocationPoint.user_id, LocationPoint.recorded_at.desc())
        )
        rows = self.db.execute(stmt).scalars().all()
        return {row.user_id: row for row in rows}

    def delete_older_than(self, *, company_id: uuid.UUID, cutoff: datetime) -> int:
        """Retention enforcement: purge points recorded before ``cutoff`` for
        one company. Returns the number of rows deleted."""
        stmt = delete(LocationPoint).where(
            LocationPoint.company_id == company_id, LocationPoint.recorded_at < cutoff
        )
        result = self.db.execute(stmt)
        return result.rowcount or 0
