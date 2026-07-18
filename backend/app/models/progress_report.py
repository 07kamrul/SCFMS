"""Daily progress reports: stage-wise self-reported progress + notes.

Immutable once submitted — no update/delete, matching the append-only
historical-record pattern used elsewhere (ActivityLog, Assignment history).
"""
from __future__ import annotations

import uuid
from datetime import date as date_
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.progress_report_stage_entry import ProgressReportStageEntry
    from app.models.project import Project


class DailyProgressReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_progress_reports"
    __table_args__ = (
        CheckConstraint(
            "overall_progress_percent IS NULL OR "
            "(overall_progress_percent >= 0 AND overall_progress_percent <= 100)",
            name="overall_progress_percent_range",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    report_date: Mapped[date_] = mapped_column(Date, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Self-reported overall figure for the day. When given, it becomes the
    # parent Project's current progress_percent (see ProgressReportService.create).
    overall_progress_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)

    project: Mapped["Project"] = relationship()
    stage_entries: Mapped[list["ProgressReportStageEntry"]] = relationship(
        order_by="ProgressReportStageEntry.created_at",
        cascade="all, delete-orphan",
    )
