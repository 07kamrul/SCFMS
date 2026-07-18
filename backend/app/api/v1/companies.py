"""Company registration (public) and settings management (owner-only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.user import User
from app.permissions.roles import Permission
from app.schemas.auth import UserPublic
from app.schemas.common import Envelope, ok
from app.schemas.company import (
    CompanyPublic,
    CompanyRegister,
    CompanySettingsPublic,
    CompanySettingsUpdate,
)
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


class _RegisterResult(CompanyPublic):
    pass


@router.post(
    "/register",
    response_model=Envelope[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Self-service: create a company and its owner account",
)
def register(payload: CompanyRegister, db: Session = Depends(get_db)) -> Envelope[dict]:
    company, owner = CompanyService(db).register(payload)
    return ok(
        {
            "company": CompanyPublic.model_validate(company).model_dump(mode="json"),
            "owner": UserPublic.model_validate(owner).model_dump(mode="json"),
        }
    )


@router.get("/settings", response_model=Envelope[CompanySettingsPublic])
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.COMPANY_VIEW)),
) -> Envelope[CompanySettingsPublic]:
    row = CompanyService(db).get_settings(current_user.company_id)
    return ok(CompanySettingsPublic.model_validate(row))


@router.patch("/settings", response_model=Envelope[CompanySettingsPublic])
def update_settings(
    payload: CompanySettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.COMPANY_MANAGE_SETTINGS)),
) -> Envelope[CompanySettingsPublic]:
    row = CompanyService(db).update_settings(current_user.company_id, payload)
    return ok(CompanySettingsPublic.model_validate(row))
