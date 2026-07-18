"""Employee <-> project assignment history.

Rows are never deleted or mutated in place except to set `ended_at` — this is
how "full history preserved on transfer" works: ending an assignment and
starting a new one are two immutable rows, not an overwrite. A user may hold
several concurrent active assignments (different projects); the partial
unique index below only blocks a duplicate *active* row for the same
(user, project) pair.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AssignmentRole

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class Assignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assignments"
    __table_args__ = (
        Index(
            "uq_assignments_active_user_project",
            "user_id",
            "project_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Who created this assignment (HR Admin/Owner) — audit only, no back-populated
    # relationship, same minimal pattern as ActivityLog.actor_user_id.
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    role: Mapped[AssignmentRole] = mapped_column(
        SAEnum(
            AssignmentRole,
            name="assignment_role",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="assignments")
    user: Mapped["User"] = relationship(
        back_populates="assignments", foreign_keys=[user_id]
    )
