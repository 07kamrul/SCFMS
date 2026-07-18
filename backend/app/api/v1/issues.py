"""Issue reporting: categories, priorities, status history, comments, photos."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.enums import IssueCategory, IssuePriority, IssueStatus
from app.models.user import User
from app.permissions.roles import Permission, has_permission
from app.schemas.common import Envelope, PaginationParams, ok
from app.schemas.issue import (
    IssueCommentCreate,
    IssueCommentPublic,
    IssueCreate,
    IssuePhotoCreate,
    IssuePhotoPublic,
    IssuePublic,
    IssueStatusHistoryPublic,
    IssueUpdate,
)
from app.services.issue_service import IssueService

router = APIRouter(prefix="/issues", tags=["issues"])


def _view_flags(user: User) -> tuple[bool, bool]:
    """(can_view_all_projects, can_view_all_issues)."""
    return (
        has_permission(user.role, Permission.PROJECT_VIEW_ALL),
        has_permission(user.role, Permission.ISSUE_UPDATE),
    )


@router.post("", response_model=Envelope[IssuePublic], status_code=201)
def create_issue(
    payload: IssueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ISSUE_CREATE)),
) -> Envelope[IssuePublic]:
    issue = IssueService(db).create(
        company_id=current_user.company_id, reported_by_user_id=current_user.id, payload=payload
    )
    return ok(IssuePublic.model_validate(issue))


@router.get("", response_model=Envelope[list[IssuePublic]])
def list_issues(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ISSUE_VIEW)),
    project_id: uuid.UUID | None = Query(default=None),
    status: IssueStatus | None = Query(default=None),
    priority: IssuePriority | None = Query(default=None),
    category: IssueCategory | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Envelope[list[IssuePublic]]:
    can_view_all_projects, can_view_all_issues = _view_flags(current_user)
    pagination = PaginationParams(page=page, page_size=page_size)
    rows, total = IssueService(db).list(
        company_id=current_user.company_id,
        current_user_id=current_user.id,
        can_view_all_projects=can_view_all_projects,
        can_view_all_issues=can_view_all_issues,
        project_id=project_id,
        status=status,
        priority=priority,
        category=category,
        pagination=pagination,
    )
    return ok([IssuePublic.model_validate(r) for r in rows], meta=pagination.to_meta(total))


@router.get("/{issue_id}", response_model=Envelope[IssuePublic])
def get_issue(
    issue_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ISSUE_VIEW)),
) -> Envelope[IssuePublic]:
    can_view_all_projects, can_view_all_issues = _view_flags(current_user)
    issue = IssueService(db).get_visible(
        company_id=current_user.company_id,
        issue_id=issue_id,
        current_user_id=current_user.id,
        can_view_all_projects=can_view_all_projects,
        can_view_all_issues=can_view_all_issues,
    )
    return ok(IssuePublic.model_validate(issue))


@router.patch("/{issue_id}", response_model=Envelope[IssuePublic])
def update_issue(
    issue_id: uuid.UUID,
    payload: IssueUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ISSUE_UPDATE)),
) -> Envelope[IssuePublic]:
    issue = IssueService(db).update(
        company_id=current_user.company_id,
        issue_id=issue_id,
        payload=payload,
        changed_by_user_id=current_user.id,
    )
    return ok(IssuePublic.model_validate(issue))


@router.get("/{issue_id}/history", response_model=Envelope[list[IssueStatusHistoryPublic]])
def list_issue_history(
    issue_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ISSUE_VIEW)),
) -> Envelope[list[IssueStatusHistoryPublic]]:
    can_view_all_projects, can_view_all_issues = _view_flags(current_user)
    service = IssueService(db)
    issue = service.get_visible(
        company_id=current_user.company_id,
        issue_id=issue_id,
        current_user_id=current_user.id,
        can_view_all_projects=can_view_all_projects,
        can_view_all_issues=can_view_all_issues,
    )
    return ok([IssueStatusHistoryPublic.model_validate(h) for h in service.list_history(issue=issue)])


@router.get("/{issue_id}/comments", response_model=Envelope[list[IssueCommentPublic]])
def list_issue_comments(
    issue_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ISSUE_VIEW)),
) -> Envelope[list[IssueCommentPublic]]:
    can_view_all_projects, can_view_all_issues = _view_flags(current_user)
    service = IssueService(db)
    issue = service.get_visible(
        company_id=current_user.company_id,
        issue_id=issue_id,
        current_user_id=current_user.id,
        can_view_all_projects=can_view_all_projects,
        can_view_all_issues=can_view_all_issues,
    )
    return ok([IssueCommentPublic.model_validate(c) for c in service.list_comments(issue=issue)])


@router.post("/{issue_id}/comments", response_model=Envelope[IssueCommentPublic], status_code=201)
def create_issue_comment(
    issue_id: uuid.UUID,
    payload: IssueCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ISSUE_VIEW)),
) -> Envelope[IssueCommentPublic]:
    can_view_all_projects, can_view_all_issues = _view_flags(current_user)
    service = IssueService(db)
    issue = service.get_visible(
        company_id=current_user.company_id,
        issue_id=issue_id,
        current_user_id=current_user.id,
        can_view_all_projects=can_view_all_projects,
        can_view_all_issues=can_view_all_issues,
    )
    comment = service.add_comment(issue=issue, user_id=current_user.id, payload=payload)
    return ok(IssueCommentPublic.model_validate(comment))


@router.get("/{issue_id}/photos", response_model=Envelope[list[IssuePhotoPublic]])
def list_issue_photos(
    issue_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ISSUE_VIEW)),
) -> Envelope[list[IssuePhotoPublic]]:
    can_view_all_projects, can_view_all_issues = _view_flags(current_user)
    service = IssueService(db)
    issue = service.get_visible(
        company_id=current_user.company_id,
        issue_id=issue_id,
        current_user_id=current_user.id,
        can_view_all_projects=can_view_all_projects,
        can_view_all_issues=can_view_all_issues,
    )
    return ok([IssuePhotoPublic.model_validate(p) for p in service.list_photos(issue=issue)])


@router.post("/{issue_id}/photos", response_model=Envelope[IssuePhotoPublic], status_code=201)
def create_issue_photo(
    issue_id: uuid.UUID,
    payload: IssuePhotoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PHOTO_UPLOAD)),
) -> Envelope[IssuePhotoPublic]:
    can_view_all_projects, can_view_all_issues = _view_flags(current_user)
    service = IssueService(db)
    issue = service.get_visible(
        company_id=current_user.company_id,
        issue_id=issue_id,
        current_user_id=current_user.id,
        can_view_all_projects=can_view_all_projects,
        can_view_all_issues=can_view_all_issues,
    )
    photo = service.add_photo(issue=issue, user_id=current_user.id, payload=payload)
    return ok(IssuePhotoPublic.model_validate(photo))
