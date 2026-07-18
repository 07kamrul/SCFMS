"""Issue, status-history, comment, and photo data access, always tenant-scoped."""
from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import func, or_, select

from app.models.enums import IssueCategory, IssuePriority, IssueStatus
from app.models.issue import Issue
from app.models.issue_comment import IssueComment
from app.models.issue_photo import IssuePhoto
from app.models.issue_status_history import IssueStatusHistory
from app.repositories.base import BaseRepository


class IssueRepository(BaseRepository[Issue]):
    model = Issue

    def list_for_company(
        self,
        *,
        company_id: uuid.UUID,
        project_ids: Iterable[uuid.UUID] | None = None,
        mine_user_id: uuid.UUID | None = None,
        status: IssueStatus | None = None,
        priority: IssuePriority | None = None,
        category: IssueCategory | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Issue], int]:
        base = select(Issue).where(Issue.company_id == company_id)
        if project_ids is not None:
            base = base.where(Issue.project_id.in_(project_ids))
        if mine_user_id is not None:
            base = base.where(
                or_(
                    Issue.reported_by_user_id == mine_user_id,
                    Issue.assigned_to_user_id == mine_user_id,
                )
            )
        if status:
            base = base.where(Issue.status == status)
        if priority:
            base = base.where(Issue.priority == priority)
        if category:
            base = base.where(Issue.category == category)
        total = int(
            self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        )
        rows = list(
            self.db.execute(
                base.order_by(Issue.created_at.desc()).offset(offset).limit(limit)
            ).scalars().all()
        )
        return rows, total


class IssueStatusHistoryRepository(BaseRepository[IssueStatusHistory]):
    model = IssueStatusHistory

    def list_for_issue(self, *, issue_id: uuid.UUID) -> list[IssueStatusHistory]:
        stmt = (
            select(IssueStatusHistory)
            .where(IssueStatusHistory.issue_id == issue_id)
            .order_by(IssueStatusHistory.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())


class IssueCommentRepository(BaseRepository[IssueComment]):
    model = IssueComment

    def list_for_issue(self, *, issue_id: uuid.UUID) -> list[IssueComment]:
        stmt = (
            select(IssueComment)
            .where(IssueComment.issue_id == issue_id)
            .order_by(IssueComment.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())


class IssuePhotoRepository(BaseRepository[IssuePhoto]):
    model = IssuePhoto

    def list_for_issue(self, *, issue_id: uuid.UUID) -> list[IssuePhoto]:
        stmt = (
            select(IssuePhoto)
            .where(IssuePhoto.issue_id == issue_id)
            .order_by(IssuePhoto.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())
