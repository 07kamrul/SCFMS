"""Milestone 5: tasks (workflow, comments, photos) and issues (status history,
categories, comments, photos).

Revision ID: 0005_tasks_and_issues
Revises: 0004_location_tracking
Create Date: 2026-09-01
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_tasks_and_issues"
down_revision: str | None = "0004_location_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


task_status_enum = postgresql.ENUM(
    "todo", "in_progress", "blocked", "submitted", "approved", "rejected", "completed", "cancelled",
    name="task_status",
    create_type=False,
)
task_priority_enum = postgresql.ENUM(
    "low", "medium", "high", "urgent", name="task_priority", create_type=False
)
issue_status_enum = postgresql.ENUM(
    "open", "assigned", "in_progress", "waiting", "resolved", "closed", "reopened",
    name="issue_status",
    create_type=False,
)
issue_priority_enum = postgresql.ENUM(
    "low", "medium", "high", "critical", name="issue_priority", create_type=False
)
issue_category_enum = postgresql.ENUM(
    "work_delay", "design_problem", "worker_shortage", "site_access_problem", "client_change",
    "weather", "quality_problem", "utility_problem", "approval_problem", "other",
    name="issue_category",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    task_status_enum.create(bind, checkfirst=True)
    task_priority_enum.create(bind, checkfirst=True)
    issue_status_enum.create(bind, checkfirst=True)
    issue_priority_enum.create(bind, checkfirst=True)
    issue_category_enum.create(bind, checkfirst=True)

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", task_status_enum, server_default=sa.text("'todo'"), nullable=False),
        sa.Column("priority", task_priority_enum, server_default=sa.text("'medium'"), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_tasks_company_id_companies", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_tasks_project_id_projects", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], name="fk_tasks_assigned_to_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_tasks_created_by_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_tasks"),
    )
    op.create_index("ix_tasks_company_id", "tasks", ["company_id"])
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_assigned_to_user_id", "tasks", ["assigned_to_user_id"])

    op.create_table(
        "task_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_task_comments_company_id_companies", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], name="fk_task_comments_task_id_tasks", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_task_comments_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_task_comments"),
    )
    op.create_index("ix_task_comments_company_id", "task_comments", ["company_id"])
    op.create_index("ix_task_comments_task_id", "task_comments", ["task_id"])

    op.create_table(
        "task_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("photo_url", sa.String(length=500), nullable=False),
        sa.Column("caption", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_task_photos_company_id_companies", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], name="fk_task_photos_task_id_tasks", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_task_photos_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_task_photos"),
    )
    op.create_index("ix_task_photos_company_id", "task_photos", ["company_id"])
    op.create_index("ix_task_photos_task_id", "task_photos", ["task_id"])

    op.create_table(
        "issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reported_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", issue_category_enum, nullable=False),
        sa.Column("priority", issue_priority_enum, server_default=sa.text("'medium'"), nullable=False),
        sa.Column("status", issue_status_enum, server_default=sa.text("'open'"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_issues_company_id_companies", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_issues_project_id_projects", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reported_by_user_id"], ["users.id"], name="fk_issues_reported_by_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], name="fk_issues_assigned_to_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_issues"),
    )
    op.create_index("ix_issues_company_id", "issues", ["company_id"])
    op.create_index("ix_issues_project_id", "issues", ["project_id"])
    op.create_index("ix_issues_reported_by_user_id", "issues", ["reported_by_user_id"])
    op.create_index("ix_issues_assigned_to_user_id", "issues", ["assigned_to_user_id"])

    op.create_table(
        "issue_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_status", issue_status_enum, nullable=True),
        sa.Column("to_status", issue_status_enum, nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_issue_status_history_company_id_companies", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], name="fk_issue_status_history_issue_id_issues", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], name="fk_issue_status_history_changed_by_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_issue_status_history"),
    )
    op.create_index("ix_issue_status_history_company_id", "issue_status_history", ["company_id"])
    op.create_index("ix_issue_status_history_issue_id", "issue_status_history", ["issue_id"])

    op.create_table(
        "issue_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_issue_comments_company_id_companies", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], name="fk_issue_comments_issue_id_issues", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_issue_comments_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_issue_comments"),
    )
    op.create_index("ix_issue_comments_company_id", "issue_comments", ["company_id"])
    op.create_index("ix_issue_comments_issue_id", "issue_comments", ["issue_id"])

    op.create_table(
        "issue_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("photo_url", sa.String(length=500), nullable=False),
        sa.Column("caption", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_issue_photos_company_id_companies", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], name="fk_issue_photos_issue_id_issues", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_issue_photos_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_issue_photos"),
    )
    op.create_index("ix_issue_photos_company_id", "issue_photos", ["company_id"])
    op.create_index("ix_issue_photos_issue_id", "issue_photos", ["issue_id"])


def downgrade() -> None:
    op.drop_table("issue_photos")
    op.drop_table("issue_comments")
    op.drop_table("issue_status_history")
    op.drop_table("issues")
    op.drop_table("task_photos")
    op.drop_table("task_comments")
    op.drop_table("tasks")

    bind = op.get_bind()
    issue_category_enum.drop(bind, checkfirst=True)
    issue_priority_enum.drop(bind, checkfirst=True)
    issue_status_enum.drop(bind, checkfirst=True)
    task_priority_enum.drop(bind, checkfirst=True)
    task_status_enum.drop(bind, checkfirst=True)
