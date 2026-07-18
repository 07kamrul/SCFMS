"""Project data access, always tenant-scoped."""
from __future__ import annotations

import uuid
from collections.abc import Iterable

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select

from app.models.enums import ProjectStatus
from app.models.project import Project
from app.repositories.base import BaseRepository


def _point_expr(*, lat: float, lng: float):
    """Build the point directly in SQL from plain floats — avoids any
    ambiguity around binding a Python geoalchemy2 element as a parameter."""
    return func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)


class ProjectRepository(BaseRepository[Project]):
    model = Project

    def list_for_company(
        self,
        *,
        company_id: uuid.UUID,
        status: ProjectStatus | None = None,
        search: str | None = None,
        project_ids: Iterable[uuid.UUID] | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Project], int]:
        base = select(Project).where(Project.company_id == company_id)
        if project_ids is not None:
            base = base.where(Project.id.in_(project_ids))
        if status:
            base = base.where(Project.status == status)
        if search:
            like = f"%{search.lower()}%"
            base = base.where(func.lower(Project.name).like(like))
        total = int(
            self.db.execute(
                select(func.count()).select_from(base.subquery())
            ).scalar_one()
        )
        rows = list(
            self.db.execute(
                base.order_by(Project.name).offset(offset).limit(limit)
            ).scalars().all()
        )
        return rows, total

    def list_all_for_company(
        self, company_id: uuid.UUID, *, project_ids: Iterable[uuid.UUID] | None = None
    ) -> list[Project]:
        """Unpaginated — feeds the all-projects status-colored map view."""
        stmt = select(Project).where(Project.company_id == company_id)
        if project_ids is not None:
            stmt = stmt.where(Project.id.in_(project_ids))
        return list(self.db.execute(stmt.order_by(Project.name)).scalars().all())

    def find_inside(
        self,
        *,
        company_id: uuid.UUID,
        lat: float,
        lng: float,
        project_ids: Iterable[uuid.UUID] | None = None,
    ) -> list[Project]:
        """Projects (with a drawn boundary) whose polygon contains this point."""
        point = _point_expr(lat=lat, lng=lng)
        stmt = select(Project).where(
            Project.company_id == company_id,
            Project.boundary.isnot(None),
            Project.boundary.ST_Contains(point),
        )
        if project_ids is not None:
            stmt = stmt.where(Project.id.in_(project_ids))
        return list(self.db.execute(stmt).scalars().all())

    def find_near(
        self,
        *,
        company_id: uuid.UUID,
        lat: float,
        lng: float,
        distance_meters: float,
        project_ids: Iterable[uuid.UUID] | None = None,
    ) -> list[Project]:
        """Projects within `distance_meters` of this point (geography cast —
        true spheroid distance in meters, not degrees)."""
        point = _point_expr(lat=lat, lng=lng)
        stmt = select(Project).where(
            Project.company_id == company_id,
            Project.boundary.isnot(None),
            cast(Project.boundary, Geography).ST_DWithin(
                cast(point, Geography), distance_meters
            ),
        )
        if project_ids is not None:
            stmt = stmt.where(Project.id.in_(project_ids))
        return list(self.db.execute(stmt).scalars().all())
