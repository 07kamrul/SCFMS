"""Assignment schemas: create/transfer payloads and the public representation."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AssignmentRole


class AssignmentCreate(BaseModel):
    project_id: uuid.UUID
    user_id: uuid.UUID
    role: AssignmentRole


class AssignmentTransfer(BaseModel):
    new_project_id: uuid.UUID
    role: AssignmentRole


class AssignmentPublic(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    assigned_by_user_id: uuid.UUID | None
    role: AssignmentRole
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
