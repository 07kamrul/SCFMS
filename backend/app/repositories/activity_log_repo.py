"""Append-only audit-trail writes."""
from __future__ import annotations

import uuid

from app.models.activity_log import ActivityLog
from app.repositories.base import BaseRepository


class ActivityLogRepository(BaseRepository[ActivityLog]):
    model = ActivityLog

    def log(
        self,
        *,
        company_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        action: str,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        description: str | None = None,
        context: dict | None = None,
    ) -> ActivityLog:
        entry = ActivityLog(
            company_id=company_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            context=context,
        )
        self.add(entry)
        return entry
