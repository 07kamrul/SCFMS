"""GPS location submission and server-computed geofence status."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_any_permission, require_permission
from app.db.session import get_db
from app.models.user import User
from app.permissions.roles import Permission, has_permission
from app.schemas.common import Envelope, ok
from app.schemas.location import (
    LocationConsentPublic,
    LocationPointCreate,
    LocationPointPublic,
    LocationStatusPublic,
    TeamMemberStatus,
)
from app.services.location_service import LocationService

router = APIRouter(prefix="/locations", tags=["locations"])

_VIEW_TEAM = (Permission.TRACKING_VIEW_ALL, Permission.TRACKING_VIEW_ASSIGNED)


@router.post("/consent", response_model=Envelope[LocationConsentPublic], status_code=201)
def grant_location_consent(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.LOCATION_SHARE)),
) -> Envelope[LocationConsentPublic]:
    """Must be called once before this user's device can submit any location
    point (see LocationService.submit_point). Revisitable — consent can be
    re-granted after being revoked by an admin clearing the field."""
    user = LocationService(db).record_consent(
        company_id=current_user.company_id, user_id=current_user.id
    )
    return ok(LocationConsentPublic(consented_at=user.location_consent_at))


@router.post("", response_model=Envelope[LocationStatusPublic], status_code=201)
def submit_location(
    payload: LocationPointCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.LOCATION_SHARE)),
) -> Envelope[LocationStatusPublic]:
    service = LocationService(db)
    service.submit_point(
        company_id=current_user.company_id, user_id=current_user.id, payload=payload
    )
    status, point = service.get_status_for_user(
        company_id=current_user.company_id, user_id=current_user.id
    )
    return ok(
        LocationStatusPublic(
            status=status,
            point=LocationPointPublic.model_validate(point) if point else None,
        )
    )


@router.get("/me", response_model=Envelope[LocationStatusPublic])
def get_my_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TRACKING_VIEW_SELF)),
) -> Envelope[LocationStatusPublic]:
    status, point = LocationService(db).get_status_for_user(
        company_id=current_user.company_id, user_id=current_user.id
    )
    return ok(
        LocationStatusPublic(
            status=status,
            point=LocationPointPublic.model_validate(point) if point else None,
        )
    )


@router.get("/team", response_model=Envelope[list[TeamMemberStatus]])
def get_team_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_permission(*_VIEW_TEAM)),
) -> Envelope[list[TeamMemberStatus]]:
    """Feeds the live employee map: status-colored markers for every user the
    caller's tracking-permission tier makes visible (see LocationService.team_status)."""
    rows = LocationService(db).team_status(
        company_id=current_user.company_id,
        current_user_id=current_user.id,
        can_view_all_tracking=has_permission(current_user.role, Permission.TRACKING_VIEW_ALL),
        can_view_all_projects=has_permission(current_user.role, Permission.PROJECT_VIEW_ALL),
    )
    return ok(
        [
            TeamMemberStatus(
                user_id=user.id,
                full_name=user.full_name,
                role=user.role,
                status=status,
                point=LocationPointPublic.model_validate(point) if point else None,
            )
            for user, status, point in rows
        ]
    )
