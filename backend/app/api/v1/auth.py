"""Authentication endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    TokenPair,
    UserPublic,
)
from app.schemas.common import Envelope, ok
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Envelope[LoginResponse])
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Envelope[LoginResponse]:
    result = AuthService(db).login(
        email=payload.email,
        phone=payload.phone,
        password=payload.password,
        device_id=payload.device_id,
    )
    return ok(result)


@router.post("/refresh", response_model=Envelope[TokenPair])
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> Envelope[TokenPair]:
    tokens = AuthService(db).refresh(
        raw_refresh_token=payload.refresh_token, device_id=None
    )
    return ok(tokens)


@router.post("/logout", response_model=Envelope[dict], status_code=status.HTTP_200_OK)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> Envelope[dict]:
    AuthService(db).logout(raw_refresh_token=payload.refresh_token)
    return ok({"detail": "Logged out."})


@router.post("/logout-all", response_model=Envelope[dict])
def logout_all(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Envelope[dict]:
    AuthService(db).logout_all(user_id=current_user.id)
    return ok({"detail": "All sessions revoked."})


@router.get("/me", response_model=Envelope[UserPublic])
def me(current_user: User = Depends(get_current_user)) -> Envelope[UserPublic]:
    return ok(UserPublic.model_validate(current_user))


@router.post("/change-password", response_model=Envelope[dict])
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Envelope[dict]:
    AuthService(db).change_password(
        user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return ok({"detail": "Password changed. Please log in again on other devices."})
