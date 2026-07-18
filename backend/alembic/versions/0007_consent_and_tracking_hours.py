"""Milestone 4 hardening: location consent and configurable tracking-hours default.

Revision ID: 0007_consent_and_tracking_hours
Revises: 0006_progress_reports
Create Date: 2026-10-01
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_consent_and_tracking_hours"
down_revision: str | None = "0006_progress_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("location_consent_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Widen the tracking-hours default to unrestricted (0-24): the column was
    # never actually enforced before this migration, so existing rows keep
    # whatever value they have; only the default for *new* companies changes.
    op.alter_column(
        "company_settings", "tracking_start_hour", server_default=sa.text("0")
    )
    op.alter_column(
        "company_settings", "tracking_end_hour", server_default=sa.text("24")
    )


def downgrade() -> None:
    op.alter_column(
        "company_settings", "tracking_end_hour", server_default=sa.text("20")
    )
    op.alter_column(
        "company_settings", "tracking_start_hour", server_default=sa.text("6")
    )
    op.drop_column("users", "location_consent_at")
