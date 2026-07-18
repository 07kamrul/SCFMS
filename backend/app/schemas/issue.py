"""Issue, status-history, comment, and photo schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import IssueCategory, IssuePriority, IssueStatus


class IssueCreate(BaseModel):
    project_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    category: IssueCategory
    priority: IssuePriority = IssuePriority.MEDIUM
    assigned_to_user_id: uuid.UUID | None = None


class IssueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    category: IssueCategory | None = None
    priority: IssuePriority | None = None
    status: IssueStatus | None = None
    assigned_to_user_id: uuid.UUID | None = None
    # Optional note attached to the status-history entry when status changes.
    note: str | None = Field(default=None, max_length=2000)


class IssuePublic(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    project_id: uuid.UUID
    reported_by_user_id: uuid.UUID | None
    assigned_to_user_id: uuid.UUID | None
    title: str
    description: str | None
    category: IssueCategory
    priority: IssuePriority
    status: IssueStatus
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IssueStatusHistoryPublic(BaseModel):
    id: uuid.UUID
    issue_id: uuid.UUID
    from_status: IssueStatus | None
    to_status: IssueStatus
    changed_by_user_id: uuid.UUID | None
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class IssueCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class IssueCommentPublic(BaseModel):
    id: uuid.UUID
    issue_id: uuid.UUID
    user_id: uuid.UUID | None
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class IssuePhotoCreate(BaseModel):
    photo_url: str = Field(min_length=1, max_length=500)
    caption: str | None = Field(default=None, max_length=500)


class IssuePhotoPublic(BaseModel):
    id: uuid.UUID
    issue_id: uuid.UUID
    user_id: uuid.UUID | None
    photo_url: str
    caption: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
