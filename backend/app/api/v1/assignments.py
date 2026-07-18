"""Employee <-> project assignments: assign/end/transfer, with history."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.permissions.roles import Permission
from app.schemas.assignment import AssignmentCreate, AssignmentPublic, AssignmentTransfer
from app.schemas.common import Envelope, PaginationParams, ok
from app.services.assignment_service import AssignmentService

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.post("", response_model=Envelope[AssignmentPublic], status_code=201)
def create_assignment(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ASSIGNMENT_MANAGE)),
) -> Envelope[AssignmentPublic]:
    assignment = AssignmentService(db).assign(
        company_id=current_user.company_id,
        payload=payload,
        assigned_by_user_id=current_user.id,
    )
    return ok(AssignmentPublic.model_validate(assignment))


@router.get("", response_model=Envelope[list[AssignmentPublic]])
def list_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ASSIGNMENT_VIEW)),
    project_id: uuid.UUID | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    active_only: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Envelope[list[AssignmentPublic]]:
    pagination = PaginationParams(page=page, page_size=page_size)
    rows, total = AssignmentService(db).list(
        company_id=current_user.company_id,
        project_id=project_id,
        user_id=user_id,
        active_only=active_only,
        pagination=pagination,
    )
    return ok(
        [AssignmentPublic.model_validate(r) for r in rows],
        meta=pagination.to_meta(total),
    )


@router.get("/me", response_model=Envelope[list[AssignmentPublic]])
def list_my_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Envelope[list[AssignmentPublic]]:
    """Every role can see its own assignment history, even roles (e.g.
    Employee) that lack ASSIGNMENT_VIEW over the full company roster."""
    rows = AssignmentService(db).list_for_user(
        company_id=current_user.company_id, user_id=current_user.id
    )
    return ok([AssignmentPublic.model_validate(r) for r in rows])


@router.post("/{assignment_id}/end", response_model=Envelope[AssignmentPublic])
def end_assignment(
    assignment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ASSIGNMENT_MANAGE)),
) -> Envelope[AssignmentPublic]:
    assignment = AssignmentService(db).end(
        company_id=current_user.company_id, assignment_id=assignment_id
    )
    return ok(AssignmentPublic.model_validate(assignment))


@router.post("/{assignment_id}/transfer", response_model=Envelope[AssignmentPublic])
def transfer_assignment(
    assignment_id: uuid.UUID,
    payload: AssignmentTransfer,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ASSIGNMENT_MANAGE)),
) -> Envelope[AssignmentPublic]:
    """Ends the current assignment and creates a new one atomically — the old
    row is preserved as history, never overwritten."""
    assignment = AssignmentService(db).transfer(
        company_id=current_user.company_id,
        assignment_id=assignment_id,
        payload=payload,
        assigned_by_user_id=current_user.id,
    )
    return ok(AssignmentPublic.model_validate(assignment))
