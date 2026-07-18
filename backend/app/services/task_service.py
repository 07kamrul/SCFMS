"""Task management: create/assign/update, comments, photos.

Visibility mirrors ProjectService: a task is only visible if its project is
visible. Within a visible project, TASK_CREATE holders (Owner/PE/SE) see
every task; everyone else (Employee) sees only tasks assigned to them.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.enums import TaskPriority, TaskStatus
from app.models.task import Task
from app.models.task_comment import TaskComment
from app.models.task_photo import TaskPhoto
from app.repositories.assignment_repo import AssignmentRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.task_repo import TaskCommentRepository, TaskPhotoRepository, TaskRepository
from app.repositories.user_repo import UserRepository
from app.schemas.common import PaginationParams
from app.schemas.task import TaskCommentCreate, TaskCreate, TaskPhotoCreate, TaskUpdate

_APPROVAL_GATED_STATUSES = {TaskStatus.APPROVED, TaskStatus.REJECTED, TaskStatus.COMPLETED}


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.tasks = TaskRepository(db)
        self.comments = TaskCommentRepository(db)
        self.photos = TaskPhotoRepository(db)
        self.projects = ProjectRepository(db)
        self.assignments = AssignmentRepository(db)
        self.users = UserRepository(db)

    def create(
        self, *, company_id: uuid.UUID, created_by_user_id: uuid.UUID, payload: TaskCreate
    ) -> Task:
        if self.projects.get_for_company(payload.project_id, company_id) is None:
            raise NotFoundError("Project not found.")
        if payload.assigned_to_user_id is not None:
            if self.users.get_for_company(payload.assigned_to_user_id, company_id) is None:
                raise NotFoundError("Assignee not found.")

        task = Task(
            company_id=company_id,
            project_id=payload.project_id,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            assigned_to_user_id=payload.assigned_to_user_id,
            due_date=payload.due_date,
            created_by_user_id=created_by_user_id,
        )
        self.tasks.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def _visible_project_ids(
        self, *, company_id: uuid.UUID, current_user_id: uuid.UUID, can_view_all_projects: bool
    ) -> set[uuid.UUID] | None:
        """None means "every company project" (unbounded)."""
        if can_view_all_projects:
            return None
        return self.assignments.active_project_ids_for_user(
            company_id=company_id, user_id=current_user_id
        )

    def get_visible(
        self,
        *,
        company_id: uuid.UUID,
        task_id: uuid.UUID,
        current_user_id: uuid.UUID,
        can_view_all_projects: bool,
        can_view_all_tasks: bool,
    ) -> Task:
        task = self.tasks.get_for_company(task_id, company_id)
        if task is None:
            raise NotFoundError("Task not found.")
        project_ids = self._visible_project_ids(
            company_id=company_id,
            current_user_id=current_user_id,
            can_view_all_projects=can_view_all_projects,
        )
        if project_ids is not None and task.project_id not in project_ids:
            raise NotFoundError("Task not found.")
        if not can_view_all_tasks and task.assigned_to_user_id != current_user_id:
            raise NotFoundError("Task not found.")
        return task

    def list(
        self,
        *,
        company_id: uuid.UUID,
        current_user_id: uuid.UUID,
        can_view_all_projects: bool,
        can_view_all_tasks: bool,
        project_id: uuid.UUID | None,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        overdue_only: bool,
        pagination: PaginationParams,
    ) -> tuple[list[Task], int]:
        project_ids = self._visible_project_ids(
            company_id=company_id,
            current_user_id=current_user_id,
            can_view_all_projects=can_view_all_projects,
        )
        if project_id is not None:
            # Narrow further to a single project, but never escape the
            # caller's visible scope.
            if project_ids is not None and project_id not in project_ids:
                return [], 0
            project_ids = {project_id}
        if project_ids is not None and not project_ids:
            return [], 0

        assigned_to_user_id = None if can_view_all_tasks else current_user_id
        return self.tasks.list_for_company(
            company_id=company_id,
            project_ids=project_ids,
            assigned_to_user_id=assigned_to_user_id,
            status=status,
            priority=priority,
            overdue_only=overdue_only,
            offset=pagination.offset,
            limit=pagination.page_size,
        )

    def update(
        self,
        *,
        company_id: uuid.UUID,
        task_id: uuid.UUID,
        payload: TaskUpdate,
        can_approve: bool,
        can_reassign: bool,
    ) -> Task:
        task = self.tasks.get_for_company(task_id, company_id)
        if task is None:
            raise NotFoundError("Task not found.")
        data = payload.model_dump(exclude_unset=True)

        if "status" in data and data["status"] in _APPROVAL_GATED_STATUSES and not can_approve:
            raise PermissionDeniedError(
                "Only an approver can move a task to approved, rejected, or completed."
            )
        if "assigned_to_user_id" in data and data["assigned_to_user_id"] != task.assigned_to_user_id:
            if not can_reassign:
                raise PermissionDeniedError("You cannot reassign this task to someone else.")
            new_assignee = data["assigned_to_user_id"]
            if new_assignee is not None and self.users.get_for_company(new_assignee, company_id) is None:
                raise NotFoundError("Assignee not found.")

        for key, value in data.items():
            setattr(task, key, value)
        self.db.commit()
        self.db.refresh(task)
        return task

    def add_comment(
        self, *, task: Task, user_id: uuid.UUID, payload: TaskCommentCreate
    ) -> TaskComment:
        comment = TaskComment(
            company_id=task.company_id, task_id=task.id, user_id=user_id, body=payload.body
        )
        self.comments.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def list_comments(self, *, task: Task) -> list[TaskComment]:
        return self.comments.list_for_task(task_id=task.id)

    def add_photo(
        self, *, task: Task, user_id: uuid.UUID, payload: TaskPhotoCreate
    ) -> TaskPhoto:
        photo = TaskPhoto(
            company_id=task.company_id,
            task_id=task.id,
            user_id=user_id,
            photo_url=payload.photo_url,
            caption=payload.caption,
        )
        self.photos.add(photo)
        self.db.commit()
        self.db.refresh(photo)
        return photo

    def list_photos(self, *, task: Task) -> list[TaskPhoto]:
        return self.photos.list_for_task(task_id=task.id)
