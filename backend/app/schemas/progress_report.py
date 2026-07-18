"""Daily progress report, stage-entry, and photo schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class StageEntryCreate(BaseModel):
    stage_name: str = Field(min_length=1, max_length=120)
    progress_percent: int = Field(ge=0, le=100)
    notes: str | None = Field(default=None, max_length=2000)


class StageEntryPublic(BaseModel):
    id: uuid.UUID
    stage_name: str
    progress_percent: int
    notes: str | None

    model_config = {"from_attributes": True}


class ProgressReportCreate(BaseModel):
    project_id: uuid.UUID
    report_date: date
    summary: str | None = Field(default=None, max_length=5000)
    overall_progress_percent: int | None = Field(default=None, ge=0, le=100)
    stage_entries: list[StageEntryCreate] = Field(default_factory=list)


class ProgressReportPublic(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    project_id: uuid.UUID
    submitted_by_user_id: uuid.UUID | None
    report_date: date
    summary: str | None
    overall_progress_percent: int | None
    created_at: datetime
    stage_entries: list[StageEntryPublic] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ProgressPhotoCreate(BaseModel):
    photo_url: str = Field(min_length=1, max_length=500)
    caption: str | None = Field(default=None, max_length=500)


class ProgressPhotoPublic(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    report_id: uuid.UUID
    user_id: uuid.UUID | None
    photo_url: str
    caption: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
