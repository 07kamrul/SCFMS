"""User/employee management endpoints (HR Admin & Owner)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.enums import Role, UserStatus
from app.models.user import User
from app.permissions.roles import Permission
from app.schemas.auth import UserPublic
from app.schemas.common import Envelope, PaginationParams, ok
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=Envelope[UserPublic], status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USER_CREATE)),
) -> Envelope[UserPublic]:
    user = UserService(db).create(company_id=current_user.company_id, payload=payload)
    return ok(UserPublic.model_validate(user))


@router.get("", response_model=Envelope[list[UserPublic]])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USER_VIEW)),
    role: Role | None = Query(default=None),
    search: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Envelope[list[UserPublic]]:
    pagination = PaginationParams(page=page, page_size=page_size)
    rows, total = UserService(db).list(
        company_id=current_user.company_id,
        role=role,
        search=search,
        pagination=pagination,
    )
    return ok(
        [UserPublic.model_validate(r) for r in rows],
        meta=pagination.to_meta(total),
    )


@router.get("/{user_id}", response_model=Envelope[UserPublic])
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USER_VIEW)),
) -> Envelope[UserPublic]:
    user = UserService(db).get(company_id=current_user.company_id, user_id=user_id)
    return ok(UserPublic.model_validate(user))


@router.patch("/{user_id}", response_model=Envelope[UserPublic])
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USER_UPDATE)),
) -> Envelope[UserPublic]:
    user = UserService(db).update(
        company_id=current_user.company_id, user_id=user_id, payload=payload
    )
    return ok(UserPublic.model_validate(user))


@router.post("/{user_id}/deactivate", response_model=Envelope[UserPublic])
def deactivate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USER_DEACTIVATE)),
) -> Envelope[UserPublic]:
    user = UserService(db).set_status(
        company_id=current_user.company_id, user_id=user_id, status=UserStatus.INACTIVE
    )
    return ok(UserPublic.model_validate(user))


@router.post("/{user_id}/activate", response_model=Envelope[UserPublic])
def activate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USER_DEACTIVATE)),
) -> Envelope[UserPublic]:
    user = UserService(db).set_status(
        company_id=current_user.company_id, user_id=user_id, status=UserStatus.ACTIVE
    )
    return ok(UserPublic.model_validate(user))


@router.post("/{user_id}/reset-password", response_model=Envelope[dict])
def reset_password(
    user_id: uuid.UUID,
    new_password: str = Query(min_length=8, max_length=128),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USER_RESET_PASSWORD)),
) -> Envelope[dict]:
    UserService(db).reset_password(
        company_id=current_user.company_id, user_id=user_id, new_password=new_password
    )
    return ok({"detail": "Password reset. User's sessions were revoked."})
