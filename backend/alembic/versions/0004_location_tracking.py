"""Milestone 4: GPS location points and geofence-tracking settings.

Revision ID: 0004_location_tracking
Revises: 0003_assignments
Create Date: 2026-08-15
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "0004_location_tracking"
down_revision: str | None = "0003_assignments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "company_settings",
        sa.Column(
            "offline_after_minutes", sa.Integer(), server_default=sa.text("15"), nullable=False
        ),
    )

    op.create_table(
        "location_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "point",
            Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("accuracy_meters", sa.Float(), nullable=True),
        sa.Column("is_mock_location", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("battery_percent", sa.Integer(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # Bare name: the "ck" naming convention wraps this as
        # ck_location_points_battery_percent_range — see the matching note in
        # migration 0002 for why the full name must NOT be passed here.
        sa.CheckConstraint(
            "battery_percent IS NULL OR (battery_percent >= 0 AND battery_percent <= 100)",
            name="battery_percent_range",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name="fk_location_points_company_id_companies", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_location_points_user_id_users", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_location_points"),
    )
    op.create_index("ix_location_points_company_id", "location_points", ["company_id"])
    op.create_index("ix_location_points_user_id", "location_points", ["user_id"])
    op.create_index(
        "ix_location_points_user_recorded", "location_points", ["user_id", "recorded_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_location_points_user_recorded", table_name="location_points")
    op.drop_index("ix_location_points_user_id", table_name="location_points")
    op.drop_index("ix_location_points_company_id", table_name="location_points")
    op.drop_table("location_points")
    op.drop_column("company_settings", "offline_after_minutes")
