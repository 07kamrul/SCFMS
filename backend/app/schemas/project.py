"""Project schemas: create/update payloads and the public representation.

The site-boundary polygon is exchanged over the API as GeoJSON so an
OpenStreetMap-drawing client (web or mobile) can consume/produce it directly.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import ProjectStatus
from app.utils.geo import to_geojson_polygon


class GeoJSONPolygon(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[list[float]]]

    @field_validator("coordinates")
    @classmethod
    def _validate_ring(cls, v: list[list[list[float]]]) -> list[list[list[float]]]:
        if not v or len(v[0]) < 4:
            raise ValueError("A polygon ring needs at least 4 positions (closed ring).")
        if v[0][0] != v[0][-1]:
            raise ValueError("Polygon ring must be closed (first and last positions equal).")
        return v


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: ProjectStatus = ProjectStatus.PLANNED
    boundary: GeoJSONPolygon | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: ProjectStatus | None = None
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    boundary: GeoJSONPolygon | None = None


class ProjectPublic(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    description: str | None
    status: ProjectStatus
    progress_percent: int
    boundary: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _convert_orm_boundary(cls, obj: Any) -> Any:
        if isinstance(obj, dict):
            return obj
        return {
            "id": obj.id,
            "company_id": obj.company_id,
            "name": obj.name,
            "description": obj.description,
            "status": obj.status,
            "progress_percent": obj.progress_percent,
            "boundary": to_geojson_polygon(obj.boundary),
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
        }
