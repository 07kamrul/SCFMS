"""Milestone 2: projects with a GIS site-boundary polygon.

Revision ID: 0002_projects
Revises: 0001_initial
Create Date: 2026-07-25
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "0002_projects"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


project_status_enum = postgresql.ENUM(
    "planned", "running", "on_hold", "delayed", "completed", "archived",
    name="project_status",
    create_type=False,
)


def upgrade() -> None:
    # Deferred here from migration 0001 (see its comment): the foundation
    # tables use no spatial types, so PostGIS is enabled starting with the
    # first migration that actually introduces a geometry column.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    bind = op.get_bind()
    project_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", project_status_enum, server_default=sa.text("'planned'"), nullable=False),
        sa.Column("progress_percent", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "boundary",
            Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # Bare name: env.py passes target_metadata (with its naming_convention)
        # into context.configure(), so Alembic re-applies the "ck" template to
        # whatever name is given here — the full ck_projects_... name would
        # get double-prefixed. See the matching comment in models/project.py.
        sa.CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="progress_percent_range",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name="fk_projects_company_id_companies", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
    )
    op.create_index("ix_projects_company_id", "projects", ["company_id"])
    op.create_index(
        "idx_projects_boundary", "projects", ["boundary"], postgresql_using="gist"
    )


def downgrade() -> None:
    # PostGIS itself is left enabled: later milestones also depend on it, so
    # its lifecycle isn't tied to this single migration.
    op.drop_index("idx_projects_boundary", table_name="projects")
    op.drop_index("ix_projects_company_id", table_name="projects")
    op.drop_table("projects")
    bind = op.get_bind()
    project_status_enum.drop(bind, checkfirst=True)
