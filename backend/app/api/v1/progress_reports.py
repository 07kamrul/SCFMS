"""Daily progress reports: stage-wise progress, photo timeline per project."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.user import User
from app.permissions.roles import Permission, has_permission
from app.schemas.common import Envelope, PaginationParams, ok
from app.schemas.progress_report import (
    ProgressPhotoCreate,
    ProgressPhotoPublic,
    ProgressReportCreate,
    ProgressReportPublic,
)
from app.services.progress_report_service import ProgressReportService

router = APIRouter(prefix="/progress-reports", tags=["progress-reports"])


def _can_view_all_projects(user: User) -> bool:
    return has_permission(user.role, Permission.PROJECT_VIEW_ALL)


@router.post("", response_model=Envelope[ProgressReportPublic], status_code=201)
def create_progress_report(
    payload: ProgressReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PROGRESS_SUBMIT)),
) -> Envelope[ProgressReportPublic]:
    report = ProgressReportService(db).create(
        company_id=current_user.company_id,
        submitted_by_user_id=current_user.id,
        payload=payload,
    )
    return ok(ProgressReportPublic.model_validate(report))


@router.get("", response_model=Envelope[list[ProgressReportPublic]])
def list_progress_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PROGRESS_VIEW)),
    project_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Envelope[list[ProgressReportPublic]]:
    pagination = PaginationParams(page=page, page_size=page_size)
    rows, total = ProgressReportService(db).list(
        company_id=current_user.company_id,
        current_user_id=current_user.id,
        can_view_all_projects=_can_view_all_projects(current_user),
        project_id=project_id,
        pagination=pagination,
    )
    return ok([ProgressReportPublic.model_validate(r) for r in rows], meta=pagination.to_meta(total))


@router.get("/timeline", response_model=Envelope[list[ProgressPhotoPublic]])
def get_project_photo_timeline(
    project_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PROGRESS_VIEW)),
) -> Envelope[list[ProgressPhotoPublic]]:
    photos = ProgressReportService(db).project_photo_timeline(
        company_id=current_user.company_id,
        project_id=project_id,
        current_user_id=current_user.id,
        can_view_all_projects=_can_view_all_projects(current_user),
    )
    return ok([ProgressPhotoPublic.model_validate(p) for p in photos])


@router.get("/{report_id}", response_model=Envelope[ProgressReportPublic])
def get_progress_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PROGRESS_VIEW)),
) -> Envelope[ProgressReportPublic]:
    report = ProgressReportService(db).get_visible(
        company_id=current_user.company_id,
        report_id=report_id,
        current_user_id=current_user.id,
        can_view_all_projects=_can_view_all_projects(current_user),
    )
    return ok(ProgressReportPublic.model_validate(report))


@router.get("/{report_id}/photos", response_model=Envelope[list[ProgressPhotoPublic]])
def list_progress_report_photos(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PROGRESS_VIEW)),
) -> Envelope[list[ProgressPhotoPublic]]:
    service = ProgressReportService(db)
    report = service.get_visible(
        company_id=current_user.company_id,
        report_id=report_id,
        current_user_id=current_user.id,
        can_view_all_projects=_can_view_all_projects(current_user),
    )
    return ok([ProgressPhotoPublic.model_validate(p) for p in service.list_photos(report=report)])


@router.post("/{report_id}/photos", response_model=Envelope[ProgressPhotoPublic], status_code=201)
def create_progress_report_photo(
    report_id: uuid.UUID,
    payload: ProgressPhotoCreate,
    db: Session = Depends(get_db),
    # Gated on PROGRESS_VIEW rather than PHOTO_UPLOAD: Employee holds
    # PHOTO_UPLOAD (for task/issue photos) but not PROGRESS_VIEW, and has no
    # legitimate access to progress reports at all. Every role that does
    # have PROGRESS_VIEW (Owner/PE/SE) already holds PHOTO_UPLOAD too.
    current_user: User = Depends(require_permission(Permission.PROGRESS_VIEW)),
) -> Envelope[ProgressPhotoPublic]:
    service = ProgressReportService(db)
    report = service.get_visible(
        company_id=current_user.company_id,
        report_id=report_id,
        current_user_id=current_user.id,
        can_view_all_projects=_can_view_all_projects(current_user),
    )
    photo = service.add_photo(report=report, user_id=current_user.id, payload=payload)
    return ok(ProgressPhotoPublic.model_validate(photo))
