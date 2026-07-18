"""Raw GPS points submitted by employees. Append-only, never updated.

Deliberately has NO ORM relationship back from User — this table is a
time-series log that can grow very large, and a lazy `user.location_points`
list would be an easy way to accidentally load a user's entire GPS history.
Always query it directly through LocationPointRepository instead.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class LocationPoint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "location_points"
    __table_args__ = (
        CheckConstraint(
            "battery_percent IS NULL OR (battery_percent >= 0 AND battery_percent <= 100)",
            name="battery_percent_range",
        ),
        Index("ix_location_points_user_recorded", "user_id", "recorded_at"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    point: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    accuracy_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_mock_location: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    battery_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Client-supplied GPS fix time. `created_at` (TimestampMixin) doubles as
    # the server-received time — no separate received_at column.
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
