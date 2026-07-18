"""Stage-wise progress line items within a daily progress report.

Stage names are free text, not a canonical per-project stage list — the PRD
explicitly calls simple self-reported per-stage progress acceptable for v1,
with a configurable weighting model deferred to a later phase.
"""
from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ProgressReportStageEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "progress_report_stage_entries"
    __table_args__ = (
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="progress_percent_range",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        # Explicit shortened name: the auto-generated
        # "..._report_id_daily_progress_reports" form is 65 bytes, over
        # Postgres's 63-byte identifier limit — must match migration 0006.
        ForeignKey(
            "daily_progress_reports.id",
            ondelete="CASCADE",
            name="fk_progress_report_stage_entries_report_id_progress_reports",
        ),
        nullable=False,
        index=True,
    )

    stage_name: Mapped[str] = mapped_column(String(120), nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
