"""Initial multi-tenant foundation: PostGIS, companies, users, RBAC, tokens.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-18
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# create_type=False: these types are created/dropped explicitly below, so
# create_table must NOT also try to emit CREATE TYPE (which would duplicate it).
role_enum = postgresql.ENUM(
    "company_owner",
    "hr_admin",
    "project_engineer",
    "site_engineer",
    "employee",
    name="role",
    create_type=False,
)
user_status_enum = postgresql.ENUM(
    "active", "inactive", "suspended", name="user_status", create_type=False
)


def upgrade() -> None:
    # NOTE: PostGIS is enabled by the Milestone-2 migration that first
    # introduces geometry columns (project boundaries). The foundation tables
    # use no spatial types, so this migration runs on vanilla PostgreSQL too.
    bind = op.get_bind()
    role_enum.create(bind, checkfirst=True)
    user_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_companies"),
        sa.UniqueConstraint("slug", name="uq_companies_slug"),
    )
    op.create_index("ix_companies_slug", "companies", ["slug"], unique=True)

    op.create_table(
        "company_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("near_distance_meters", sa.Integer(), server_default=sa.text("300"), nullable=False),
        sa.Column("tracking_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("tracking_start_hour", sa.Integer(), server_default=sa.text("6"), nullable=False),
        sa.Column("tracking_end_hour", sa.Integer(), server_default=sa.text("20"), nullable=False),
        sa.Column("location_retention_days", sa.Integer(), server_default=sa.text("90"), nullable=False),
        sa.Column("allow_multiple_devices", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name="fk_company_settings_company_id_companies", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_company_settings"),
        sa.UniqueConstraint("company_id", name="uq_company_settings_company_id"),
    )
    op.create_index("ix_company_settings_company_id", "company_settings", ["company_id"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("status", user_status_enum, server_default=sa.text("'active'"), nullable=False),
        sa.Column("profile_photo_url", sa.String(length=500), nullable=True),
        sa.Column("job_title", sa.String(length=120), nullable=True),
        sa.Column("is_identity_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("failed_login_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name="fk_users_company_id_companies", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("company_id", "email", name="uq_users_company_id_email"),
        sa.UniqueConstraint("company_id", "phone", name="uq_users_company_id_phone"),
    )
    op.create_index("ix_users_company_id", "users", ["company_id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("device_id", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_refresh_tokens_user_id_users", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name="fk_refresh_tokens_company_id_companies", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_company_id", "refresh_tokens", ["company_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    op.create_table(
        "activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("context", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name="fk_activity_logs_company_id_companies", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"],
            name="fk_activity_logs_actor_user_id_users", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_activity_logs"),
    )
    op.create_index("ix_activity_logs_company_id", "activity_logs", ["company_id"])
    op.create_index("ix_activity_logs_actor_user_id", "activity_logs", ["actor_user_id"])
    op.create_index("ix_activity_logs_action", "activity_logs", ["action"])


def downgrade() -> None:
    op.drop_table("activity_logs")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("company_settings")
    op.drop_table("companies")
    bind = op.get_bind()
    user_status_enum.drop(bind, checkfirst=True)
    role_enum.drop(bind, checkfirst=True)
