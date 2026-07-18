"""Task, task-comment, and task-photo data access, always tenant-scoped."""
from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import func, select

from app.models.enums import TaskPriority, TaskStatus
from app.models.task import TERMINAL_TASK_STATUSES, Task
from app.models.task_comment import TaskComment
from app.models.task_photo import TaskPhoto
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    model = Task

    def list_for_company(
        self,
        *,
        company_id: uuid.UUID,
        project_ids: Iterable[uuid.UUID] | None = None,
        assigned_to_user_id: uuid.UUID | None = None,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        overdue_only: bool = False,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Task], int]:
        base = select(Task).where(Task.company_id == company_id)
        if project_ids is not None:
            base = base.where(Task.project_id.in_(project_ids))
        if assigned_to_user_id is not None:
            base = base.where(Task.assigned_to_user_id == assigned_to_user_id)
        if status:
            base = base.where(Task.status == status)
        if priority:
            base = base.where(Task.priority == priority)
        if overdue_only:
            base = base.where(
                Task.due_date.isnot(None),
                Task.due_date < func.now(),
                Task.status.notin_(TERMINAL_TASK_STATUSES),
            )
        total = int(
            self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        )
        rows = list(
            self.db.execute(
                base.order_by(Task.created_at.desc()).offset(offset).limit(limit)
            ).scalars().all()
        )
        return rows, total


class TaskCommentRepository(BaseRepository[TaskComment]):
    model = TaskComment

    def list_for_task(self, *, task_id: uuid.UUID) -> list[TaskComment]:
        stmt = (
            select(TaskComment)
            .where(TaskComment.task_id == task_id)
            .order_by(TaskComment.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())


class TaskPhotoRepository(BaseRepository[TaskPhoto]):
    model = TaskPhoto

    def list_for_task(self, *, task_id: uuid.UUID) -> list[TaskPhoto]:
        stmt = (
            select(TaskPhoto)
            .where(TaskPhoto.task_id == task_id)
            .order_by(TaskPhoto.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())
