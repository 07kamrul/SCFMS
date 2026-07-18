"""Task, task-comment, and task-photo schemas."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field, computed_field

from app.models.enums import TaskPriority, TaskStatus
from app.models.task import TERMINAL_TASK_STATUSES


class TaskCreate(BaseModel):
    project_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_to_user_id: uuid.UUID | None = None
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assigned_to_user_id: uuid.UUID | None = None
    due_date: datetime | None = None


class TaskPublic(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    project_id: uuid.UUID
    assigned_to_user_id: uuid.UUID | None
    created_by_user_id: uuid.UUID | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_overdue(self) -> bool:
        if self.due_date is None or self.status in TERMINAL_TASK_STATUSES:
            return False
        return self.due_date < datetime.now(timezone.utc)


class TaskCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class TaskCommentPublic(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID | None
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskPhotoCreate(BaseModel):
    photo_url: str = Field(min_length=1, max_length=500)
    caption: str | None = Field(default=None, max_length=500)


class TaskPhotoPublic(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID | None
    photo_url: str
    caption: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
