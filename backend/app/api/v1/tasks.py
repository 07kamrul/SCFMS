"""Task management: create/assign/update, comments, photos."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.enums import TaskPriority, TaskStatus
from app.models.user import User
from app.permissions.roles import Permission, has_permission
from app.schemas.common import Envelope, PaginationParams, ok
from app.schemas.task import (
    TaskCommentCreate,
    TaskCommentPublic,
    TaskCreate,
    TaskPhotoCreate,
    TaskPhotoPublic,
    TaskPublic,
    TaskUpdate,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _view_flags(user: User) -> tuple[bool, bool]:
    """(can_view_all_projects, can_view_all_tasks)."""
    return (
        has_permission(user.role, Permission.PROJECT_VIEW_ALL),
        has_permission(user.role, Permission.TASK_CREATE),
    )


@router.post("", response_model=Envelope[TaskPublic], status_code=201)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TASK_CREATE)),
) -> Envelope[TaskPublic]:
    task = TaskService(db).create(
        company_id=current_user.company_id, created_by_user_id=current_user.id, payload=payload
    )
    return ok(TaskPublic.model_validate(task))


@router.get("", response_model=Envelope[list[TaskPublic]])
def list_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TASK_VIEW)),
    project_id: uuid.UUID | None = Query(default=None),
    status: TaskStatus | None = Query(default=None),
    priority: TaskPriority | None = Query(default=None),
    overdue: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Envelope[list[TaskPublic]]:
    can_view_all_projects, can_view_all_tasks = _view_flags(current_user)
    pagination = PaginationParams(page=page, page_size=page_size)
    rows, total = TaskService(db).list(
        company_id=current_user.company_id,
        current_user_id=current_user.id,
        can_view_all_projects=can_view_all_projects,
        can_view_all_tasks=can_view_all_tasks,
        project_id=project_id,
        status=status,
        priority=priority,
        overdue_only=overdue,
        pagination=pagination,
    )
    return ok([TaskPublic.model_validate(r) for r in rows], meta=pagination.to_meta(total))


@router.get("/{task_id}", response_model=Envelope[TaskPublic])
def get_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TASK_VIEW)),
) -> Envelope[TaskPublic]:
    can_view_all_projects, can_view_all_tasks = _view_flags(current_user)
    task = TaskService(db).get_visible(
        company_id=current_user.company_id,
        task_id=task_id,
        current_user_id=current_user.id,
        can_view_all_projects=can_view_all_projects,
        can_view_all_tasks=can_view_all_tasks,
    )
    return ok(TaskPublic.model_validate(task))


@router.patch("/{task_id}", response_model=Envelope[TaskPublic])
def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TASK_UPDATE)),
) -> Envelope[TaskPublic]:
    task = TaskService(db).update(
        company_id=current_user.company_id,
        task_id=task_id,
        payload=payload,
        can_approve=has_permission(current_user.role, Permission.TASK_APPROVE),
        can_reassign=has_permission(current_user.role, Permission.TASK_CREATE),
    )
    return ok(TaskPublic.model_validate(task))


@router.get("/{task_id}/comments", response_model=Envelope[list[TaskCommentPublic]])
def list_task_comments(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TASK_VIEW)),
) -> Envelope[list[TaskCommentPublic]]:
    can_view_all_projects, can_view_all_tasks = _view_flags(current_user)
    service = TaskService(db)
    task = service.get_visible(
        company_id=current_user.company_id,
        task_id=task_id,
        current_user_id=current_user.id,
        can_view_all_projects=can_view_all_projects,
        can_view_all_tasks=can_view_all_tasks,
    )
    return ok([TaskCommentPublic.model_validate(c) for c in service.list_comments(task=task)])


@router.post("/{task_id}/comments", response_model=Envelope[TaskCommentPublic], status_code=201)
def create_task_comment(
    task_id: uuid.UUID,
    payload: TaskCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TASK_VIEW)),
) -> Envelope[TaskCommentPublic]:
    can_view_all_projects, can_view_all_tasks = _view_flags(current_user)
    service = TaskService(db)
    task = service.get_visible(
        company_id=current_user.company_id,
        task_id=task_id,
        current_user_id=current_user.id,
        can_view_all_projects=can_view_all_projects,
        can_view_all_tasks=can_view_all_tasks,
    )
    comment = service.add_comment(task=task, user_id=current_user.id, payload=payload)
    return ok(TaskCommentPublic.model_validate(comment))


@router.get("/{task_id}/photos", response_model=Envelope[list[TaskPhotoPublic]])
def list_task_photos(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TASK_VIEW)),
) -> Envelope[list[TaskPhotoPublic]]:
    can_view_all_projects, can_view_all_tasks = _view_flags(current_user)
    service = TaskService(db)
    task = service.get_visible(
        company_id=current_user.company_id,
        task_id=task_id,
        current_user_id=current_user.id,
        can_view_all_projects=can_view_all_projects,
        can_view_all_tasks=can_view_all_tasks,
    )
    return ok([TaskPhotoPublic.model_validate(p) for p in service.list_photos(task=task)])


@router.post("/{task_id}/photos", response_model=Envelope[TaskPhotoPublic], status_code=201)
def create_task_photo(
    task_id: uuid.UUID,
    payload: TaskPhotoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PHOTO_UPLOAD)),
) -> Envelope[TaskPhotoPublic]:
    # PHOTO_UPLOAD gates the action; visibility is still enforced via the
    # same TASK_VIEW-equivalent scoping so you can't attach a photo to a
    # task you couldn't otherwise see.
    can_view_all_projects, can_view_all_tasks = _view_flags(current_user)
    service = TaskService(db)
    task = service.get_visible(
        company_id=current_user.company_id,
        task_id=task_id,
        current_user_id=current_user.id,
        can_view_all_projects=can_view_all_projects,
        can_view_all_tasks=can_view_all_tasks,
    )
    photo = service.add_photo(task=task, user_id=current_user.id, payload=payload)
    return ok(TaskPhotoPublic.model_validate(photo))
