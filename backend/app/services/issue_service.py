"""Issue management: create/update with auto-recorded status history, comments, photos.

Visibility mirrors TaskService: an issue is only visible if its project is
visible. Within a visible project, ISSUE_UPDATE holders (Owner/PE/SE) see
every issue; everyone else (Employee, who lacks ISSUE_UPDATE) sees only
issues they reported or are assigned to resolve.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.enums import IssueCategory, IssuePriority, IssueStatus
from app.models.issue import Issue
from app.models.issue_comment import IssueComment
from app.models.issue_photo import IssuePhoto
from app.models.issue_status_history import IssueStatusHistory
from app.repositories.assignment_repo import AssignmentRepository
from app.repositories.issue_repo import (
    IssueCommentRepository,
    IssuePhotoRepository,
    IssueRepository,
    IssueStatusHistoryRepository,
)
from app.repositories.project_repo import ProjectRepository
from app.repositories.user_repo import UserRepository
from app.schemas.common import PaginationParams
from app.schemas.issue import IssueCommentCreate, IssueCreate, IssuePhotoCreate, IssueUpdate

_RESOLVED_LIKE_STATUSES = {IssueStatus.RESOLVED, IssueStatus.CLOSED}


class IssueService:
    def __init__(self, db: Session):
        self.db = db
        self.issues = IssueRepository(db)
        self.history = IssueStatusHistoryRepository(db)
        self.comments = IssueCommentRepository(db)
        self.photos = IssuePhotoRepository(db)
        self.projects = ProjectRepository(db)
        self.assignments = AssignmentRepository(db)
        self.users = UserRepository(db)

    def create(
        self, *, company_id: uuid.UUID, reported_by_user_id: uuid.UUID, payload: IssueCreate
    ) -> Issue:
        if self.projects.get_for_company(payload.project_id, company_id) is None:
            raise NotFoundError("Project not found.")
        if payload.assigned_to_user_id is not None:
            if self.users.get_for_company(payload.assigned_to_user_id, company_id) is None:
                raise NotFoundError("Assignee not found.")

        issue = Issue(
            company_id=company_id,
            project_id=payload.project_id,
            title=payload.title,
            description=payload.description,
            category=payload.category,
            priority=payload.priority,
            assigned_to_user_id=payload.assigned_to_user_id,
            reported_by_user_id=reported_by_user_id,
        )
        self.issues.add(issue)
        self.history.add(
            IssueStatusHistory(
                company_id=company_id,
                issue_id=issue.id,
                from_status=None,
                to_status=issue.status,
                changed_by_user_id=reported_by_user_id,
            )
        )
        self.db.commit()
        self.db.refresh(issue)
        return issue

    def _visible_project_ids(
        self, *, company_id: uuid.UUID, current_user_id: uuid.UUID, can_view_all_projects: bool
    ) -> set[uuid.UUID] | None:
        if can_view_all_projects:
            return None
        return self.assignments.active_project_ids_for_user(
            company_id=company_id, user_id=current_user_id
        )

    def get_visible(
        self,
        *,
        company_id: uuid.UUID,
        issue_id: uuid.UUID,
        current_user_id: uuid.UUID,
        can_view_all_projects: bool,
        can_view_all_issues: bool,
    ) -> Issue:
        issue = self.issues.get_for_company(issue_id, company_id)
        if issue is None:
            raise NotFoundError("Issue not found.")
        project_ids = self._visible_project_ids(
            company_id=company_id,
            current_user_id=current_user_id,
            can_view_all_projects=can_view_all_projects,
        )
        if project_ids is not None and issue.project_id not in project_ids:
            raise NotFoundError("Issue not found.")
        if not can_view_all_issues and current_user_id not in (
            issue.reported_by_user_id,
            issue.assigned_to_user_id,
        ):
            raise NotFoundError("Issue not found.")
        return issue

    def list(
        self,
        *,
        company_id: uuid.UUID,
        current_user_id: uuid.UUID,
        can_view_all_projects: bool,
        can_view_all_issues: bool,
        project_id: uuid.UUID | None,
        status: IssueStatus | None,
        priority: IssuePriority | None,
        category: IssueCategory | None,
        pagination: PaginationParams,
    ) -> tuple[list[Issue], int]:
        project_ids = self._visible_project_ids(
            company_id=company_id,
            current_user_id=current_user_id,
            can_view_all_projects=can_view_all_projects,
        )
        if project_id is not None:
            if project_ids is not None and project_id not in project_ids:
                return [], 0
            project_ids = {project_id}
        if project_ids is not None and not project_ids:
            return [], 0

        mine_user_id = None if can_view_all_issues else current_user_id
        return self.issues.list_for_company(
            company_id=company_id,
            project_ids=project_ids,
            mine_user_id=mine_user_id,
            status=status,
            priority=priority,
            category=category,
            offset=pagination.offset,
            limit=pagination.page_size,
        )

    def update(
        self,
        *,
        company_id: uuid.UUID,
        issue_id: uuid.UUID,
        payload: IssueUpdate,
        changed_by_user_id: uuid.UUID,
    ) -> Issue:
        issue = self.issues.get_for_company(issue_id, company_id)
        if issue is None:
            raise NotFoundError("Issue not found.")
        data = payload.model_dump(exclude_unset=True)
        note = data.pop("note", None)

        if "assigned_to_user_id" in data and data["assigned_to_user_id"] is not None:
            if self.users.get_for_company(data["assigned_to_user_id"], company_id) is None:
                raise NotFoundError("Assignee not found.")

        new_status = data.get("status")
        if new_status is not None and new_status != issue.status:
            old_status = issue.status
            self.history.add(
                IssueStatusHistory(
                    company_id=company_id,
                    issue_id=issue.id,
                    from_status=old_status,
                    to_status=new_status,
                    changed_by_user_id=changed_by_user_id,
                    note=note,
                )
            )
            issue.resolved_at = (
                datetime.now(timezone.utc) if new_status in _RESOLVED_LIKE_STATUSES else None
            )

        for key, value in data.items():
            setattr(issue, key, value)
        self.db.commit()
        self.db.refresh(issue)
        return issue

    def list_history(self, *, issue: Issue) -> list[IssueStatusHistory]:
        return self.history.list_for_issue(issue_id=issue.id)

    def add_comment(
        self, *, issue: Issue, user_id: uuid.UUID, payload: IssueCommentCreate
    ) -> IssueComment:
        comment = IssueComment(
            company_id=issue.company_id, issue_id=issue.id, user_id=user_id, body=payload.body
        )
        self.comments.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def list_comments(self, *, issue: Issue) -> list[IssueComment]:
        return self.comments.list_for_issue(issue_id=issue.id)

    def add_photo(
        self, *, issue: Issue, user_id: uuid.UUID, payload: IssuePhotoCreate
    ) -> IssuePhoto:
        photo = IssuePhoto(
            company_id=issue.company_id,
            issue_id=issue.id,
            user_id=user_id,
            photo_url=payload.photo_url,
            caption=payload.caption,
        )
        self.photos.add(photo)
        self.db.commit()
        self.db.refresh(photo)
        return photo

    def list_photos(self, *, issue: Issue) -> list[IssuePhoto]:
        return self.photos.list_for_issue(issue_id=issue.id)
