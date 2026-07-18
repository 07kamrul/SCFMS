"""Construction project with an optional GIS site-boundary polygon."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ProjectStatus

if TYPE_CHECKING:
    from app.models.assignment import Assignment
    from app.models.company import Company


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (
        # Bare name: the "ck" naming convention (see db/base.py) wraps this as
        # ck_projects_progress_percent_range — passing the full name here
        # would get double-prefixed.
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="progress_percent_range",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(
            ProjectStatus,
            name="project_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ProjectStatus.PLANNED,
    )
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Site-boundary polygon drawn on OpenStreetMap. Nullable: a project can
    # exist before its boundary is drawn.
    boundary: Mapped[Any | None] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False),
        nullable=True,
    )

    company: Mapped["Company"] = relationship(back_populates="projects")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="project")
