"""Milestone 3: employee <-> project assignments (history preserved on transfer).

Revision ID: 0003_assignments
Revises: 0002_projects
Create Date: 2026-08-01
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_assignments"
down_revision: str | None = "0002_projects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


assignment_role_enum = postgresql.ENUM(
    "project_engineer", "site_engineer", "employee",
    name="assignment_role",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    assignment_role_enum.create(bind, checkfirst=True)

    op.create_table(
        "assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role", assignment_role_enum, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name="fk_assignments_company_id_companies", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_assignments_project_id_projects", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_assignments_user_id_users", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by_user_id"], ["users.id"],
            name="fk_assignments_assigned_by_user_id_users", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_assignments"),
    )
    op.create_index("ix_assignments_company_id", "assignments", ["company_id"])
    op.create_index("ix_assignments_project_id", "assignments", ["project_id"])
    op.create_index("ix_assignments_user_id", "assignments", ["user_id"])
    # Partial unique index: only one ACTIVE (ended_at IS NULL) assignment per
    # (user, project) pair. Multiple ended rows for the same pair are fine —
    # that's the assignment history.
    op.create_index(
        "uq_assignments_active_user_project",
        "assignments",
        ["user_id", "project_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_assignments_active_user_project", table_name="assignments")
    op.drop_index("ix_assignments_user_id", table_name="assignments")
    op.drop_index("ix_assignments_project_id", table_name="assignments")
    op.drop_index("ix_assignments_company_id", table_name="assignments")
    op.drop_table("assignments")
    bind = op.get_bind()
    assignment_role_enum.drop(bind, checkfirst=True)
