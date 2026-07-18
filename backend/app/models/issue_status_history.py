"""Append-only status-change log for issues. Never updated after insert."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import IssueStatus


class IssueStatusHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "issue_status_history"

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True
    )
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Same PG enum name as Issue.status — SQLAlchemy dedups CREATE TYPE
    # emission for repeated columns sharing one enum name within one MetaData.
    # Null from_status marks the initial creation entry.
    from_status: Mapped[IssueStatus | None] = mapped_column(
        SAEnum(IssueStatus, name="issue_status", values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    to_status: Mapped[IssueStatus] = mapped_column(
        SAEnum(IssueStatus, name="issue_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
