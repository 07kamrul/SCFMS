"""User account and the linked employee profile.

A user always belongs to exactly one company (tenant). The `role` column is
the single source of truth for RBAC — see app/permissions/roles.py for the
role → permission matrix.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Role, UserStatus

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.refresh_token import RefreshToken


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        # Email and phone are unique *within* a company, not globally.
        UniqueConstraint("company_id", "email", name="uq_users_company_id_email"),
        UniqueConstraint("company_id", "phone", name="uq_users_company_id_phone"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, name="role", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    status: Mapped[UserStatus] = mapped_column(
        SAEnum(
            UserStatus,
            name="user_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=UserStatus.ACTIVE,
    )

    # Employee profile fields (kept on user for MVP simplicity).
    profile_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_identity_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Login protection
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="users")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE
