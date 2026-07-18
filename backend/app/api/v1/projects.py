"""Project management: create/edit/archive/delete, polygon boundary, map view."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_any_permission, require_permission
from app.db.session import get_db
from app.models.enums import ProjectStatus
from app.models.user import User
from app.permissions.roles import Permission, has_permission
from app.schemas.common import Envelope, PaginationParams, ok
from app.schemas.project import ProjectCreate, ProjectPublic, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])

_VIEW_ANY = (Permission.PROJECT_VIEW_ALL, Permission.PROJECT_VIEW_ASSIGNED)


def _can_view_all(user: User) -> bool:
    return has_permission(user.role, Permission.PROJECT_VIEW_ALL)


@router.post("", response_model=Envelope[ProjectPublic], status_code=201)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PROJECT_CREATE)),
) -> Envelope[ProjectPublic]:
    project = ProjectService(db).create(company_id=current_user.company_id, payload=payload)
    return ok(ProjectPublic.model_validate(project))


@router.get("", response_model=Envelope[list[ProjectPublic]])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_permission(*_VIEW_ANY)),
    status: ProjectStatus | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Envelope[list[ProjectPublic]]:
    pagination = PaginationParams(page=page, page_size=page_size)
    rows, total = ProjectService(db).list(
        company_id=current_user.company_id,
        current_user_id=current_user.id,
        can_view_all=_can_view_all(current_user),
        status=status,
        search=search,
        pagination=pagination,
    )
    return ok(
        [ProjectPublic.model_validate(r) for r in rows],
        meta=pagination.to_meta(total),
    )


@router.get("/map", response_model=Envelope[list[ProjectPublic]])
def list_projects_for_map(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_permission(*_VIEW_ANY)),
) -> Envelope[list[ProjectPublic]]:
    """All-projects map view: every project the caller can see, unpaginated,
    status carried on each row so the client can colorize polygons."""
    rows = ProjectService(db).list_for_map(
        company_id=current_user.company_id,
        current_user_id=current_user.id,
        can_view_all=_can_view_all(current_user),
    )
    return ok([ProjectPublic.model_validate(r) for r in rows])


@router.get("/{project_id}", response_model=Envelope[ProjectPublic])
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_permission(*_VIEW_ANY)),
) -> Envelope[ProjectPublic]:
    project = ProjectService(db).get_visible(
        company_id=current_user.company_id,
        project_id=project_id,
        current_user_id=current_user.id,
        can_view_all=_can_view_all(current_user),
    )
    return ok(ProjectPublic.model_validate(project))


@router.patch("/{project_id}", response_model=Envelope[ProjectPublic])
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PROJECT_UPDATE)),
) -> Envelope[ProjectPublic]:
    project = ProjectService(db).update(
        company_id=current_user.company_id, project_id=project_id, payload=payload
    )
    return ok(ProjectPublic.model_validate(project))


@router.post("/{project_id}/archive", response_model=Envelope[ProjectPublic])
def archive_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PROJECT_ARCHIVE)),
) -> Envelope[ProjectPublic]:
    project = ProjectService(db).archive(
        company_id=current_user.company_id, project_id=project_id
    )
    return ok(ProjectPublic.model_validate(project))


@router.delete("/{project_id}", response_model=Envelope[dict])
def delete_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PROJECT_DELETE)),
) -> Envelope[dict]:
    ProjectService(db).delete(company_id=current_user.company_id, project_id=project_id)
    return ok({"detail": "Project deleted."})
