"""Assignment data access, always tenant-scoped."""
from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import func, select

from app.models.assignment import Assignment
from app.repositories.base import BaseRepository


class AssignmentRepository(BaseRepository[Assignment]):
    model = Assignment

    def get_active_for_user_and_project(
        self, *, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> Assignment | None:
        stmt = select(Assignment).where(
            Assignment.user_id == user_id,
            Assignment.project_id == project_id,
            Assignment.ended_at.is_(None),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def active_project_ids_for_user(
        self, *, company_id: uuid.UUID, user_id: uuid.UUID
    ) -> set[uuid.UUID]:
        stmt = select(Assignment.project_id).where(
            Assignment.company_id == company_id,
            Assignment.user_id == user_id,
            Assignment.ended_at.is_(None),
        )
        return set(self.db.execute(stmt).scalars().all())

    def active_user_ids_for_projects(
        self, *, company_id: uuid.UUID, project_ids: Iterable[uuid.UUID]
    ) -> set[uuid.UUID]:
        stmt = select(Assignment.user_id).where(
            Assignment.company_id == company_id,
            Assignment.project_id.in_(project_ids),
            Assignment.ended_at.is_(None),
        )
        return set(self.db.execute(stmt).scalars().all())

    def active_user_ids_for_company(self, *, company_id: uuid.UUID) -> set[uuid.UUID]:
        stmt = select(Assignment.user_id).where(
            Assignment.company_id == company_id,
            Assignment.ended_at.is_(None),
        )
        return set(self.db.execute(stmt).scalars().all())

    def list_for_user(self, *, company_id: uuid.UUID, user_id: uuid.UUID) -> list[Assignment]:
        """Unpaginated — feeds the caller's own "my assignments" view."""
        stmt = (
            select(Assignment)
            .where(Assignment.company_id == company_id, Assignment.user_id == user_id)
            .order_by(Assignment.started_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_for_company(
        self,
        *,
        company_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        active_only: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Assignment], int]:
        base = select(Assignment).where(Assignment.company_id == company_id)
        if project_id is not None:
            base = base.where(Assignment.project_id == project_id)
        if user_id is not None:
            base = base.where(Assignment.user_id == user_id)
        if active_only is True:
            base = base.where(Assignment.ended_at.is_(None))
        elif active_only is False:
            base = base.where(Assignment.ended_at.isnot(None))
        total = int(
            self.db.execute(
                select(func.count()).select_from(base.subquery())
            ).scalar_one()
        )
        rows = list(
            self.db.execute(
                base.order_by(Assignment.started_at.desc()).offset(offset).limit(limit)
            ).scalars().all()
        )
        return rows, total
