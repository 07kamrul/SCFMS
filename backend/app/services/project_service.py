"""Project management: create/edit/archive/delete, polygon boundary, map view."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import ProjectStatus
from app.models.project import Project
from app.repositories.assignment_repo import AssignmentRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.common import PaginationParams
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.utils.geo import geojson_polygon_to_wkb


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.assignments = AssignmentRepository(db)

    def create(self, *, company_id: uuid.UUID, payload: ProjectCreate) -> Project:
        project = Project(
            company_id=company_id,
            name=payload.name,
            description=payload.description,
            status=payload.status,
            boundary=self._to_boundary(
                payload.boundary.model_dump() if payload.boundary else None
            ),
        )
        self.projects.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get(self, *, company_id: uuid.UUID, project_id: uuid.UUID) -> Project:
        project = self.projects.get_for_company(project_id, company_id)
        if project is None:
            raise NotFoundError("Project not found.")
        return project

    def get_visible(
        self,
        *,
        company_id: uuid.UUID,
        project_id: uuid.UUID,
        current_user_id: uuid.UUID,
        can_view_all: bool,
    ) -> Project:
        """Single-project read gated the same way as list() — never leaks
        existence of a project outside the caller's view scope."""
        if not can_view_all:
            assigned_ids = self.assignments.active_project_ids_for_user(
                company_id=company_id, user_id=current_user_id
            )
            if project_id not in assigned_ids:
                raise NotFoundError("Project not found.")
        return self.get(company_id=company_id, project_id=project_id)

    def list(
        self,
        *,
        company_id: uuid.UUID,
        current_user_id: uuid.UUID,
        can_view_all: bool,
        status: ProjectStatus | None,
        search: str | None,
        pagination: PaginationParams,
    ) -> tuple[list[Project], int]:
        # PROJECT_VIEW_ASSIGNED scoping: caller sees only projects they
        # currently hold an active assignment on (app.models.assignment).
        project_ids = None
        if not can_view_all:
            project_ids = self.assignments.active_project_ids_for_user(
                company_id=company_id, user_id=current_user_id
            )
            if not project_ids:
                return [], 0
        return self.projects.list_for_company(
            company_id=company_id,
            status=status,
            search=search,
            project_ids=project_ids,
            offset=pagination.offset,
            limit=pagination.page_size,
        )

    def list_for_map(
        self, *, company_id: uuid.UUID, current_user_id: uuid.UUID, can_view_all: bool
    ) -> list[Project]:
        project_ids = None
        if not can_view_all:
            project_ids = self.assignments.active_project_ids_for_user(
                company_id=company_id, user_id=current_user_id
            )
            if not project_ids:
                return []
        return self.projects.list_all_for_company(company_id, project_ids=project_ids)

    def update(
        self, *, company_id: uuid.UUID, project_id: uuid.UUID, payload: ProjectUpdate
    ) -> Project:
        project = self.get(company_id=company_id, project_id=project_id)
        data = payload.model_dump(exclude_unset=True)
        if "boundary" in data:
            data["boundary"] = self._to_boundary(data["boundary"])
        for key, value in data.items():
            setattr(project, key, value)
        self.db.commit()
        self.db.refresh(project)
        return project

    def archive(self, *, company_id: uuid.UUID, project_id: uuid.UUID) -> Project:
        project = self.get(company_id=company_id, project_id=project_id)
        project.status = ProjectStatus.ARCHIVED
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete(self, *, company_id: uuid.UUID, project_id: uuid.UUID) -> None:
        project = self.get(company_id=company_id, project_id=project_id)
        self.projects.delete(project)
        self.db.commit()

    @staticmethod
    def _to_boundary(geojson: dict[str, Any] | None) -> Any:
        if geojson is None:
            return None
        try:
            return geojson_polygon_to_wkb(geojson)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
