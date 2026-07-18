"""GPS point submission and server-side geofence status computation.

Status priority (first match wins):
  1. LOCATION_DISABLED   — company has tracking disabled entirely
  2. UNKNOWN             — no location point ever submitted
  3. OFFLINE             — latest point older than the company's
                           offline_after_minutes
  4. OUTSIDE_TRACKING_HOURS — the point's recorded_at falls outside the
                           company's configured tracking-hours window
                           (0-24 default = unrestricted, opt-in only)
  5. NO_ASSIGNED_PROJECT — user holds no active assignment right now (a
                           precondition check, not a location check)
  6. INSIDE_ASSIGNED / NEAR_ASSIGNED — relative to the user's own assigned
                           projects (near = within near_distance_meters,
                           computed via a geography cast for true meters)
  7. INSIDE_OTHER_ACCESSIBLE / INSIDE_OTHER_UNAUTHORIZED — inside a different
     company project. Split by whether the TRACKED user's own role holds
     PROJECT_VIEW_ALL — an Owner/HR wandering into another site isn't really
     "unauthorized" for them the way it would be for a regular Employee.
  8. OUTSIDE_ASSIGNED    — none of the above
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import LocationStatus
from app.models.location_point import LocationPoint
from app.models.user import User
from app.permissions.roles import Permission, has_permission
from app.repositories.activity_log_repo import ActivityLogRepository
from app.repositories.assignment_repo import AssignmentRepository
from app.repositories.company_repo import CompanyRepository
from app.repositories.location_point_repo import LocationPointRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.user_repo import UserRepository
from app.schemas.location import LocationPointCreate
from app.utils.geo import latlng_to_point_wkb, point_to_latlng


class LocationService:
    def __init__(self, db: Session):
        self.db = db
        self.points = LocationPointRepository(db)
        self.assignments = AssignmentRepository(db)
        self.projects = ProjectRepository(db)
        self.users = UserRepository(db)
        self.companies = CompanyRepository(db)
        self.activity_logs = ActivityLogRepository(db)

    def record_consent(self, *, company_id: uuid.UUID, user_id: uuid.UUID) -> User:
        user = self.users.get_for_company(user_id, company_id)
        if user is None:
            raise NotFoundError("User not found.")
        user.location_consent_at = datetime.now(timezone.utc)
        self.activity_logs.log(
            company_id=company_id,
            actor_user_id=user_id,
            action="location.consent_granted",
            entity_type="user",
            entity_id=user_id,
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def submit_point(
        self, *, company_id: uuid.UUID, user_id: uuid.UUID, payload: LocationPointCreate
    ) -> LocationPoint:
        user = self.users.get_for_company(user_id, company_id)
        if user is None:
            raise NotFoundError("User not found.")
        if user.location_consent_at is None:
            raise ValidationError(
                "Location-tracking consent has not been recorded for this user.",
                error_code="consent_required",
            )
        point = LocationPoint(
            company_id=company_id,
            user_id=user_id,
            point=latlng_to_point_wkb(payload.lat, payload.lng),
            accuracy_meters=payload.accuracy_meters,
            is_mock_location=payload.is_mock_location,
            battery_percent=payload.battery_percent,
            recorded_at=payload.recorded_at,
        )
        self.points.add(point)
        self.db.commit()
        self.db.refresh(point)
        return point

    def get_status_for_user(
        self, *, company_id: uuid.UUID, user_id: uuid.UUID
    ) -> tuple[LocationStatus, LocationPoint | None]:
        user = self.users.get_for_company(user_id, company_id)
        if user is None:
            raise NotFoundError("User not found.")
        latest = self.points.get_latest_for_user(company_id=company_id, user_id=user_id)
        return self._compute_status(company_id=company_id, user=user, latest=latest)

    def team_status(
        self,
        *,
        company_id: uuid.UUID,
        current_user_id: uuid.UUID,
        can_view_all_tracking: bool,
        can_view_all_projects: bool,
    ) -> list[tuple[User, LocationStatus, LocationPoint | None]]:
        if can_view_all_tracking:
            # Owner: every active user in the company, assigned or not.
            target_users = self.users.list_active_for_company(company_id)
        elif can_view_all_projects:
            # HR Admin: sees every company project, so their tracking scope is
            # every currently-assigned user company-wide.
            user_ids = self.assignments.active_user_ids_for_company(company_id=company_id)
            target_users = self.users.list_by_ids(company_id=company_id, user_ids=user_ids)
        else:
            # Project/Site Engineer: only teammates sharing an active
            # assignment on a project the caller is themselves assigned to.
            project_ids = self.assignments.active_project_ids_for_user(
                company_id=company_id, user_id=current_user_id
            )
            user_ids = (
                self.assignments.active_user_ids_for_projects(
                    company_id=company_id, project_ids=project_ids
                )
                if project_ids
                else set()
            )
            target_users = self.users.list_by_ids(company_id=company_id, user_ids=user_ids)

        latest_by_user = self.points.get_latest_for_users(
            company_id=company_id, user_ids=[u.id for u in target_users]
        )
        results = []
        for user in target_users:
            latest = latest_by_user.get(user.id)
            status, latest = self._compute_status(company_id=company_id, user=user, latest=latest)
            results.append((user, status, latest))

        self.activity_logs.log(
            company_id=company_id,
            actor_user_id=current_user_id,
            action="location.team_status_viewed",
            entity_type="company",
            entity_id=company_id,
            context={"visible_user_count": len(results)},
        )
        self.db.commit()
        return results

    def _compute_status(
        self, *, company_id: uuid.UUID, user: User, latest: LocationPoint | None
    ) -> tuple[LocationStatus, LocationPoint | None]:
        settings_row = self.companies.get_settings(company_id)
        if settings_row is None or not settings_row.tracking_enabled:
            return LocationStatus.LOCATION_DISABLED, latest

        if latest is None:
            return LocationStatus.UNKNOWN, None

        stale_cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=settings_row.offline_after_minutes
        )
        if latest.recorded_at < stale_cutoff:
            return LocationStatus.OFFLINE, latest

        # Company-configurable work-hours window (0-24 default = unrestricted).
        # Evaluated against the point's own recorded_at hour, not "now" — the
        # policy is about when tracking happened, not when it's being viewed.
        point_hour = latest.recorded_at.astimezone(timezone.utc).hour
        if not (settings_row.tracking_start_hour <= point_hour < settings_row.tracking_end_hour):
            return LocationStatus.OUTSIDE_TRACKING_HOURS, latest

        assigned_ids = self.assignments.active_project_ids_for_user(
            company_id=company_id, user_id=user.id
        )
        if not assigned_ids:
            return LocationStatus.NO_ASSIGNED_PROJECT, latest

        lat, lng = point_to_latlng(latest.point)

        if self.projects.find_inside(
            company_id=company_id, lat=lat, lng=lng, project_ids=assigned_ids
        ):
            return LocationStatus.INSIDE_ASSIGNED, latest
        if self.projects.find_near(
            company_id=company_id,
            lat=lat,
            lng=lng,
            distance_meters=settings_row.near_distance_meters,
            project_ids=assigned_ids,
        ):
            return LocationStatus.NEAR_ASSIGNED, latest

        if self.projects.find_inside(company_id=company_id, lat=lat, lng=lng):
            if has_permission(user.role, Permission.PROJECT_VIEW_ALL):
                return LocationStatus.INSIDE_OTHER_ACCESSIBLE, latest
            return LocationStatus.INSIDE_OTHER_UNAUTHORIZED, latest

        return LocationStatus.OUTSIDE_ASSIGNED, latest
