"""Field issues: categories, priorities, status history, photos, comments."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import IssueCategory, IssuePriority, IssueStatus

if TYPE_CHECKING:
    from app.models.project import Project


class Issue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "issues"

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reported_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[IssueCategory] = mapped_column(
        SAEnum(IssueCategory, name="issue_category", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    priority: Mapped[IssuePriority] = mapped_column(
        SAEnum(IssuePriority, name="issue_priority", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=IssuePriority.MEDIUM,
    )
    status: Mapped[IssueStatus] = mapped_column(
        SAEnum(IssueStatus, name="issue_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=IssueStatus.OPEN,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship()
