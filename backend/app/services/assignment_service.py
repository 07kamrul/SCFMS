"""Assignment management: assign/end/transfer, with full history preserved.

Rows are never overwritten. "Transfer" ends the current assignment and
creates a new one in one transaction; the old row remains as history.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.assignment import Assignment
from app.repositories.assignment_repo import AssignmentRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.user_repo import UserRepository
from app.schemas.assignment import AssignmentCreate, AssignmentTransfer
from app.schemas.common import PaginationParams


class AssignmentService:
    def __init__(self, db: Session):
        self.db = db
        self.assignments = AssignmentRepository(db)
        self.projects = ProjectRepository(db)
        self.users = UserRepository(db)

    def assign(
        self,
        *,
        company_id: uuid.UUID,
        payload: AssignmentCreate,
        assigned_by_user_id: uuid.UUID,
    ) -> Assignment:
        if self.projects.get_for_company(payload.project_id, company_id) is None:
            raise NotFoundError("Project not found.")
        if self.users.get_for_company(payload.user_id, company_id) is None:
            raise NotFoundError("User not found.")
        if (
            self.assignments.get_active_for_user_and_project(
                user_id=payload.user_id, project_id=payload.project_id
            )
            is not None
        ):
            raise ConflictError("This user already has an active assignment on this project.")

        assignment = Assignment(
            company_id=company_id,
            project_id=payload.project_id,
            user_id=payload.user_id,
            role=payload.role,
            assigned_by_user_id=assigned_by_user_id,
        )
        self.assignments.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def get(self, *, company_id: uuid.UUID, assignment_id: uuid.UUID) -> Assignment:
        assignment = self.assignments.get_for_company(assignment_id, company_id)
        if assignment is None:
            raise NotFoundError("Assignment not found.")
        return assignment

    def list(
        self,
        *,
        company_id: uuid.UUID,
        project_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
        active_only: bool | None,
        pagination: PaginationParams,
    ) -> tuple[list[Assignment], int]:
        return self.assignments.list_for_company(
            company_id=company_id,
            project_id=project_id,
            user_id=user_id,
            active_only=active_only,
            offset=pagination.offset,
            limit=pagination.page_size,
        )

    def list_for_user(self, *, company_id: uuid.UUID, user_id: uuid.UUID) -> list[Assignment]:
        return self.assignments.list_for_user(company_id=company_id, user_id=user_id)

    def end(self, *, company_id: uuid.UUID, assignment_id: uuid.UUID) -> Assignment:
        assignment = self.get(company_id=company_id, assignment_id=assignment_id)
        if assignment.ended_at is not None:
            raise ConflictError("Assignment has already ended.")
        assignment.ended_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def transfer(
        self,
        *,
        company_id: uuid.UUID,
        assignment_id: uuid.UUID,
        payload: AssignmentTransfer,
        assigned_by_user_id: uuid.UUID,
    ) -> Assignment:
        old = self.get(company_id=company_id, assignment_id=assignment_id)
        if old.ended_at is not None:
            raise ConflictError("Assignment has already ended.")
        if payload.new_project_id == old.project_id:
            raise ConflictError("Cannot transfer an assignment to the same project.")
        if self.projects.get_for_company(payload.new_project_id, company_id) is None:
            raise NotFoundError("Project not found.")
        if (
            self.assignments.get_active_for_user_and_project(
                user_id=old.user_id, project_id=payload.new_project_id
            )
            is not None
        ):
            raise ConflictError(
                "This user already has an active assignment on the target project."
            )

        old.ended_at = datetime.now(timezone.utc)
        new_assignment = Assignment(
            company_id=company_id,
            project_id=payload.new_project_id,
            user_id=old.user_id,
            role=payload.role,
            assigned_by_user_id=assigned_by_user_id,
        )
        self.assignments.add(new_assignment)
        self.db.commit()
        self.db.refresh(new_assignment)
        return new_assignment

    def active_project_ids_for_user(
        self, *, company_id: uuid.UUID, user_id: uuid.UUID
    ) -> set[uuid.UUID]:
        return self.assignments.active_project_ids_for_user(
            company_id=company_id, user_id=user_id
        )
