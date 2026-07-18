"""Location schemas: GPS point submission and computed geofence status."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.enums import LocationStatus, Role
from app.utils.geo import point_to_latlng


class LocationPointCreate(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy_meters: float | None = Field(default=None, ge=0)
    recorded_at: datetime
    is_mock_location: bool = False
    battery_percent: int | None = Field(default=None, ge=0, le=100)


class LocationPointPublic(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    lat: float
    lng: float
    accuracy_meters: float | None
    is_mock_location: bool
    battery_percent: int | None
    recorded_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _convert_orm_point(cls, obj: Any) -> Any:
        if isinstance(obj, dict):
            return obj
        lat, lng = point_to_latlng(obj.point)
        return {
            "id": obj.id,
            "user_id": obj.user_id,
            "lat": lat,
            "lng": lng,
            "accuracy_meters": obj.accuracy_meters,
            "is_mock_location": obj.is_mock_location,
            "battery_percent": obj.battery_percent,
            "recorded_at": obj.recorded_at,
            "created_at": obj.created_at,
        }


class LocationStatusPublic(BaseModel):
    status: LocationStatus
    point: LocationPointPublic | None


class LocationConsentPublic(BaseModel):
    consented_at: datetime


class TeamMemberStatus(BaseModel):
    user_id: uuid.UUID
    full_name: str
    role: Role
    status: LocationStatus
    point: LocationPointPublic | None
