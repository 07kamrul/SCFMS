"""Remove the dead device_id concept: refresh_tokens.device_id and
company_settings.allow_multiple_devices were write-only/unwired (see
.claude/prds/remove-device-id.prd.md) — neither was ever read back or
enforced anywhere in the backend.

Revision ID: 0009_remove_device_id
Revises: 0008_notifications
Create Date: 2026-07-22
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_remove_device_id"
down_revision: str | None = "0008_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("refresh_tokens", "device_id")
    op.drop_column("company_settings", "allow_multiple_devices")


def downgrade() -> None:
    op.add_column(
        "company_settings",
        sa.Column("allow_multiple_devices", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "refresh_tokens",
        sa.Column("device_id", sa.String(length=255), nullable=True),
    )
