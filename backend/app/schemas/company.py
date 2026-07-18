"""Company and company-settings schemas."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


class CompanyRegister(BaseModel):
    """Public self-service registration: creates a company + its owner user."""

    company_name: str = Field(min_length=1, max_length=200)
    owner_full_name: str = Field(min_length=1, max_length=200)
    owner_email: EmailStr | None = None
    owner_phone: str | None = Field(default=None, max_length=32)
    owner_password: str = Field(min_length=8, max_length=128)


class CompanyPublic(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    address: str | None
    logo_url: str | None

    model_config = {"from_attributes": True}


class CompanySettingsPublic(BaseModel):
    near_distance_meters: int
    tracking_enabled: bool
    tracking_start_hour: int
    tracking_end_hour: int
    location_retention_days: int
    allow_multiple_devices: bool

    model_config = {"from_attributes": True}


class CompanySettingsUpdate(BaseModel):
    near_distance_meters: int | None = Field(default=None, ge=0, le=10000)
    tracking_enabled: bool | None = None
    tracking_start_hour: int | None = Field(default=None, ge=0, le=23)
    tracking_end_hour: int | None = Field(default=None, ge=0, le=23)
    location_retention_days: int | None = Field(default=None, ge=1, le=3650)
    allow_multiple_devices: bool | None = None
