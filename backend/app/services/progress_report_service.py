"""Daily progress reports: stage-wise self-reported progress, photo timeline.

Submitting an overall_progress_percent updates the parent Project's
progress_percent as a side effect — daily reports are what drives that
figure from here on (Milestone 2 left this as a forward-looking note).
Reports are immutable once created: no update/delete.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.progress_photo import ProgressPhoto
from app.models.progress_report import DailyProgressReport
from app.models.progress_report_stage_entry import ProgressReportStageEntry
from app.repositories.assignment_repo import AssignmentRepository
from app.repositories.progress_report_repo import ProgressPhotoRepository, ProgressReportRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.common import PaginationParams
from app.schemas.progress_report import ProgressPhotoCreate, ProgressReportCreate


class ProgressReportService:
    def __init__(self, db: Session):
        self.db = db
        self.reports = ProgressReportRepository(db)
        self.photos = ProgressPhotoRepository(db)
        self.projects = ProjectRepository(db)
        self.assignments = AssignmentRepository(db)

    def create(
        self,
        *,
        company_id: uuid.UUID,
        submitted_by_user_id: uuid.UUID,
        payload: ProgressReportCreate,
    ) -> DailyProgressReport:
        project = self.projects.get_for_company(payload.project_id, company_id)
        if project is None:
            raise NotFoundError("Project not found.")

        report = DailyProgressReport(
            company_id=company_id,
            project_id=payload.project_id,
            submitted_by_user_id=submitted_by_user_id,
            report_date=payload.report_date,
            summary=payload.summary,
            overall_progress_percent=payload.overall_progress_percent,
        )
        report.stage_entries = [
            ProgressReportStageEntry(
                company_id=company_id,
                stage_name=entry.stage_name,
                progress_percent=entry.progress_percent,
                notes=entry.notes,
            )
            for entry in payload.stage_entries
        ]
        self.reports.add(report)

        if payload.overall_progress_percent is not None:
            project.progress_percent = payload.overall_progress_percent

        self.db.commit()
        self.db.refresh(report)
        return report

    def _visible_project_ids(
        self, *, company_id: uuid.UUID, current_user_id: uuid.UUID, can_view_all_projects: bool
    ) -> set[uuid.UUID] | None:
        if can_view_all_projects:
            return None
        return self.assignments.active_project_ids_for_user(
            company_id=company_id, user_id=current_user_id
        )

    def get_visible(
        self,
        *,
        company_id: uuid.UUID,
        report_id: uuid.UUID,
        current_user_id: uuid.UUID,
        can_view_all_projects: bool,
    ) -> DailyProgressReport:
        report = self.reports.get_for_company(report_id, company_id)
        if report is None:
            raise NotFoundError("Progress report not found.")
        project_ids = self._visible_project_ids(
            company_id=company_id,
            current_user_id=current_user_id,
            can_view_all_projects=can_view_all_projects,
        )
        if project_ids is not None and report.project_id not in project_ids:
            raise NotFoundError("Progress report not found.")
        return report

    def list(
        self,
        *,
        company_id: uuid.UUID,
        current_user_id: uuid.UUID,
        can_view_all_projects: bool,
        project_id: uuid.UUID | None,
        pagination: PaginationParams,
    ) -> tuple[list[DailyProgressReport], int]:
        project_ids = self._visible_project_ids(
            company_id=company_id,
            current_user_id=current_user_id,
            can_view_all_projects=can_view_all_projects,
        )
        if project_id is not None:
            if project_ids is not None and project_id not in project_ids:
                return [], 0
            project_ids = {project_id}
        if project_ids is not None and not project_ids:
            return [], 0

        return self.reports.list_for_company(
            company_id=company_id,
            project_ids=project_ids,
            offset=pagination.offset,
            limit=pagination.page_size,
        )

    def add_photo(
        self, *, report: DailyProgressReport, user_id: uuid.UUID, payload: ProgressPhotoCreate
    ) -> ProgressPhoto:
        photo = ProgressPhoto(
            company_id=report.company_id,
            project_id=report.project_id,
            report_id=report.id,
            user_id=user_id,
            photo_url=payload.photo_url,
            caption=payload.caption,
        )
        self.photos.add(photo)
        self.db.commit()
        self.db.refresh(photo)
        return photo

    def list_photos(self, *, report: DailyProgressReport) -> list[ProgressPhoto]:
        return self.photos.list_for_report(report_id=report.id)

    def project_photo_timeline(
        self,
        *,
        company_id: uuid.UUID,
        project_id: uuid.UUID,
        current_user_id: uuid.UUID,
        can_view_all_projects: bool,
    ) -> list[ProgressPhoto]:
        if self.projects.get_for_company(project_id, company_id) is None:
            raise NotFoundError("Project not found.")
        project_ids = self._visible_project_ids(
            company_id=company_id,
            current_user_id=current_user_id,
            can_view_all_projects=can_view_all_projects,
        )
        if project_ids is not None and project_id not in project_ids:
            raise NotFoundError("Project not found.")
        return self.photos.list_for_project_timeline(company_id=company_id, project_id=project_id)
