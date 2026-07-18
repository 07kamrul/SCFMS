"""Daily progress report and photo data access, always tenant-scoped."""
from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import func, select

from app.models.progress_photo import ProgressPhoto
from app.models.progress_report import DailyProgressReport
from app.repositories.base import BaseRepository


class ProgressReportRepository(BaseRepository[DailyProgressReport]):
    model = DailyProgressReport

    def list_for_company(
        self,
        *,
        company_id: uuid.UUID,
        project_ids: Iterable[uuid.UUID] | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[DailyProgressReport], int]:
        base = select(DailyProgressReport).where(DailyProgressReport.company_id == company_id)
        if project_ids is not None:
            base = base.where(DailyProgressReport.project_id.in_(project_ids))
        total = int(
            self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        )
        rows = list(
            self.db.execute(
                base.order_by(DailyProgressReport.report_date.desc(), DailyProgressReport.created_at.desc())
                .offset(offset)
                .limit(limit)
            ).scalars().all()
        )
        return rows, total


class ProgressPhotoRepository(BaseRepository[ProgressPhoto]):
    model = ProgressPhoto

    def list_for_report(self, *, report_id: uuid.UUID) -> list[ProgressPhoto]:
        stmt = (
            select(ProgressPhoto)
            .where(ProgressPhoto.report_id == report_id)
            .order_by(ProgressPhoto.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_for_project_timeline(
        self, *, company_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[ProgressPhoto]:
        stmt = (
            select(ProgressPhoto)
            .where(ProgressPhoto.company_id == company_id, ProgressPhoto.project_id == project_id)
            .order_by(ProgressPhoto.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())
