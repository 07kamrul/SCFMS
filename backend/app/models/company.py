"""Company (tenant) and per-company settings."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="company")
    projects: Mapped[list["Project"]] = relationship(back_populates="company")
    company_settings: Mapped["CompanySettings"] = relationship(
        back_populates="company",
        uselist=False,
        cascade="all, delete-orphan",
    )


class CompanySettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "company_settings"

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Geofence / tracking policy — company-configurable.
    near_distance_meters: Mapped[int] = mapped_column(
        Integer, nullable=False, default=settings.DEFAULT_NEAR_DISTANCE_METERS
    )
    tracking_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Unrestricted (0-24) by default — a company opts into a narrower work-hours
    # window explicitly; nobody should get surprise "outside tracking hours"
    # rejections from a default they never configured.
    tracking_start_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=0)   # local hour 0-23
    tracking_end_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=24)    # exclusive upper bound, 1-24
    location_retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    # A user's latest point older than this is reported as OFFLINE rather than
    # a stale geofence status.
    offline_after_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)

    company: Mapped["Company"] = relationship(back_populates="company_settings")
