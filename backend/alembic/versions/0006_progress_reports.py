"""Milestone 6: daily progress reports, stage entries, and photo timeline.

Revision ID: 0006_progress_reports
Revises: 0005_tasks_and_issues
Create Date: 2026-09-15
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_progress_reports"
down_revision: str | None = "0005_tasks_and_issues"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_progress_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submitted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("overall_progress_percent", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "overall_progress_percent IS NULL OR "
            "(overall_progress_percent >= 0 AND overall_progress_percent <= 100)",
            name="overall_progress_percent_range",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_daily_progress_reports_company_id_companies", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_daily_progress_reports_project_id_projects", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], name="fk_daily_progress_reports_submitted_by_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_daily_progress_reports"),
    )
    op.create_index("ix_daily_progress_reports_company_id", "daily_progress_reports", ["company_id"])
    op.create_index("ix_daily_progress_reports_project_id", "daily_progress_reports", ["project_id"])
    op.create_index("ix_daily_progress_reports_submitted_by_user_id", "daily_progress_reports", ["submitted_by_user_id"])

    op.create_table(
        "progress_report_stage_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage_name", sa.String(length=120), nullable=False),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="progress_percent_range",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_progress_report_stage_entries_company_id_companies", ondelete="CASCADE"),
        # Name shortened (< 63 bytes, Postgres's identifier limit) from the
        # full "..._report_id_daily_progress_reports" auto-convention form.
        sa.ForeignKeyConstraint(["report_id"], ["daily_progress_reports.id"], name="fk_progress_report_stage_entries_report_id_progress_reports", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_progress_report_stage_entries"),
    )
    op.create_index("ix_progress_report_stage_entries_company_id", "progress_report_stage_entries", ["company_id"])
    op.create_index("ix_progress_report_stage_entries_report_id", "progress_report_stage_entries", ["report_id"])

    op.create_table(
        "progress_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("photo_url", sa.String(length=500), nullable=False),
        sa.Column("caption", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_progress_photos_company_id_companies", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_progress_photos_project_id_projects", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["daily_progress_reports.id"], name="fk_progress_photos_report_id_daily_progress_reports", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_progress_photos_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_progress_photos"),
    )
    op.create_index("ix_progress_photos_company_id", "progress_photos", ["company_id"])
    op.create_index("ix_progress_photos_project_id", "progress_photos", ["project_id"])
    op.create_index("ix_progress_photos_report_id", "progress_photos", ["report_id"])


def downgrade() -> None:
    op.drop_table("progress_photos")
    op.drop_table("progress_report_stage_entries")
    op.drop_table("daily_progress_reports")
