"""Milestone 4: GPS submission and server-computed geofence status."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.enums import AssignmentRole, Role
from app.models.user import User
from tests.factories import (
    FAR_LATLNG,
    INSIDE_LATLNG,
    NEAR_LATLNG,
    OTHER_INSIDE_LATLNG,
    OTHER_POLYGON_GEOJSON,
    SAMPLE_POLYGON_GEOJSON,
    auth_header,
    make_assignment,
    make_company,
    make_location_point,
    make_project,
    make_user,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def company(db):
    c = make_company(db, name="Trackco", slug="trackco")
    make_user(db, company=c, email="owner@trackco.com", role=Role.COMPANY_OWNER)
    make_user(db, company=c, email="hr@trackco.com", role=Role.HR_ADMIN)
    make_user(db, company=c, email="pe@trackco.com", role=Role.PROJECT_ENGINEER)
    make_user(db, company=c, email="se@trackco.com", role=Role.SITE_ENGINEER)
    make_user(db, company=c, email="emp@trackco.com", role=Role.EMPLOYEE)
    return c


def _user(db, company, email: str) -> User:
    return db.query(User).filter_by(company_id=company.id, email=email).one()


def test_project_engineer_cannot_submit_location(client, company):
    headers = auth_header(client, email="pe@trackco.com", password="password123")
    resp = client.post(
        "/api/v1/locations",
        headers=headers,
        json={"lat": 23.81, "lng": 90.41, "recorded_at": datetime.now(timezone.utc).isoformat()},
    )
    assert resp.status_code == 403


def test_employee_submit_inside_assigned_returns_status(client, company, db):
    project = make_project(db, company=company, name="Site A", boundary_geojson=SAMPLE_POLYGON_GEOJSON)
    emp = _user(db, company, "emp@trackco.com")
    make_assignment(db, company=company, project=project, user=emp, role=AssignmentRole.EMPLOYEE)
    db.commit()
    headers = auth_header(client, email="emp@trackco.com", password="password123")

    lat, lng = INSIDE_LATLNG
    resp = client.post(
        "/api/v1/locations",
        headers=headers,
        json={"lat": lat, "lng": lng, "recorded_at": datetime.now(timezone.utc).isoformat()},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["status"] == "inside_assigned"
    assert data["point"]["lat"] == pytest.approx(lat)
    assert data["point"]["lng"] == pytest.approx(lng)


def test_status_unknown_without_any_point(client, company, db):
    project = make_project(db, company=company, name="Site B", boundary_geojson=SAMPLE_POLYGON_GEOJSON)
    emp = _user(db, company, "emp@trackco.com")
    make_assignment(db, company=company, project=project, user=emp)
    db.commit()
    headers = auth_header(client, email="emp@trackco.com", password="password123")
    resp = client.get("/api/v1/locations/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "unknown"
    assert resp.json()["data"]["point"] is None


def test_status_no_assigned_project(client, company, db):
    emp = _user(db, company, "emp@trackco.com")
    make_location_point(db, company=company, user=emp, lat=INSIDE_LATLNG[0], lng=INSIDE_LATLNG[1])
    db.commit()
    headers = auth_header(client, email="emp@trackco.com", password="password123")
    resp = client.get("/api/v1/locations/me", headers=headers)
    assert resp.json()["data"]["status"] == "no_assigned_project"


def test_status_near_assigned(client, company, db):
    project = make_project(db, company=company, name="Site C", boundary_geojson=SAMPLE_POLYGON_GEOJSON)
    emp = _user(db, company, "emp@trackco.com")
    make_assignment(db, company=company, project=project, user=emp)
    make_location_point(db, company=company, user=emp, lat=NEAR_LATLNG[0], lng=NEAR_LATLNG[1])
    db.commit()
    headers = auth_header(client, email="emp@trackco.com", password="password123")
    resp = client.get("/api/v1/locations/me", headers=headers)
    assert resp.json()["data"]["status"] == "near_assigned"


def test_status_outside_assigned(client, company, db):
    project = make_project(db, company=company, name="Site D", boundary_geojson=SAMPLE_POLYGON_GEOJSON)
    emp = _user(db, company, "emp@trackco.com")
    make_assignment(db, company=company, project=project, user=emp)
    make_location_point(db, company=company, user=emp, lat=FAR_LATLNG[0], lng=FAR_LATLNG[1])
    db.commit()
    headers = auth_header(client, email="emp@trackco.com", password="password123")
    resp = client.get("/api/v1/locations/me", headers=headers)
    assert resp.json()["data"]["status"] == "outside_assigned"


def test_status_offline_overrides_geofence(client, company, db):
    """A stale point (older than offline_after_minutes) is OFFLINE even
    though it's physically inside the assigned project's boundary."""
    project = make_project(db, company=company, name="Site E", boundary_geojson=SAMPLE_POLYGON_GEOJSON)
    emp = _user(db, company, "emp@trackco.com")
    make_assignment(db, company=company, project=project, user=emp)
    stale_time = datetime.now(timezone.utc) - timedelta(hours=1)
    make_location_point(
        db, company=company, user=emp, lat=INSIDE_LATLNG[0], lng=INSIDE_LATLNG[1], recorded_at=stale_time
    )
    db.commit()
    headers = auth_header(client, email="emp@trackco.com", password="password123")
    resp = client.get("/api/v1/locations/me", headers=headers)
    assert resp.json()["data"]["status"] == "offline"


def test_status_location_disabled_overrides_everything(client, company, db):
    project = make_project(db, company=company, name="Site F", boundary_geojson=SAMPLE_POLYGON_GEOJSON)
    emp = _user(db, company, "emp@trackco.com")
    make_assignment(db, company=company, project=project, user=emp)
    make_location_point(db, company=company, user=emp, lat=INSIDE_LATLNG[0], lng=INSIDE_LATLNG[1])
    db.commit()

    owner_headers = auth_header(client, email="owner@trackco.com", password="password123")
    assert client.patch(
        "/api/v1/companies/settings", headers=owner_headers, json={"tracking_enabled": False}
    ).status_code == 200

    emp_headers = auth_header(client, email="emp@trackco.com", password="password123")
    resp = client.get("/api/v1/locations/me", headers=emp_headers)
    assert resp.json()["data"]["status"] == "location_disabled"


def test_status_inside_other_unauthorized_for_regular_employee(client, company, db):
    home = make_project(db, company=company, name="Home Site", boundary_geojson=SAMPLE_POLYGON_GEOJSON)
    make_project(db, company=company, name="Other Site", boundary_geojson=OTHER_POLYGON_GEOJSON)
    emp = _user(db, company, "emp@trackco.com")
    make_assignment(db, company=company, project=home, user=emp)
    make_location_point(
        db, company=company, user=emp, lat=OTHER_INSIDE_LATLNG[0], lng=OTHER_INSIDE_LATLNG[1]
    )
    db.commit()
    headers = auth_header(client, email="emp@trackco.com", password="password123")
    resp = client.get("/api/v1/locations/me", headers=headers)
    assert resp.json()["data"]["status"] == "inside_other_unauthorized"


def test_status_inside_other_accessible_for_project_view_all_role(client, company, db):
    """A user whose own role holds PROJECT_VIEW_ALL (e.g. the Owner) isn't
    "unauthorized" wandering into another company project."""
    home = make_project(db, company=company, name="Home Site 2", boundary_geojson=SAMPLE_POLYGON_GEOJSON)
    make_project(db, company=company, name="Other Site 2", boundary_geojson=OTHER_POLYGON_GEOJSON)
    owner = _user(db, company, "owner@trackco.com")
    # Owners aren't normally assigned, but the model allows it, and an active
    # assignment is required to reach past NO_ASSIGNED_PROJECT in the first
    # place — this exercises the accessible-vs-unauthorized branch directly.
    make_assignment(db, company=company, project=home, user=owner, role=AssignmentRole.EMPLOYEE)
    make_location_point(
        db, company=company, user=owner, lat=OTHER_INSIDE_LATLNG[0], lng=OTHER_INSIDE_LATLNG[1]
    )
    db.commit()
    headers = auth_header(client, email="owner@trackco.com", password="password123")
    resp = client.get("/api/v1/locations/me", headers=headers)
    assert resp.json()["data"]["status"] == "inside_other_accessible"


def test_hr_admin_cannot_view_own_tracking_status(client, company):
    headers = auth_header(client, email="hr@trackco.com", password="password123")
    assert client.get("/api/v1/locations/me", headers=headers).status_code == 403


def test_employee_cannot_view_team_status(client, company):
    headers = auth_header(client, email="emp@trackco.com", password="password123")
    assert client.get("/api/v1/locations/team", headers=headers).status_code == 403


def test_owner_team_view_sees_everyone_regardless_of_assignment(client, company, db):
    project = make_project(db, company=company, name="Site G", boundary_geojson=SAMPLE_POLYGON_GEOJSON)
    emp = _user(db, company, "emp@trackco.com")
    make_assignment(db, company=company, project=project, user=emp)
    db.commit()
    headers = auth_header(client, email="owner@trackco.com", password="password123")
    resp = client.get("/api/v1/locations/team", headers=headers)
    assert resp.status_code == 200
    names = {row["full_name"] for row in resp.json()["data"]}
    # HR, PE, SE, Employee should all appear even though only emp is assigned.
    assert {"Hr", "Pe", "Se", "Emp"} <= names


def test_project_engineer_team_view_scoped_to_shared_projects(client, company, db):
    shared_project = make_project(db, company=company, name="Shared Site", boundary_geojson=SAMPLE_POLYGON_GEOJSON)
    other_project = make_project(db, company=company, name="Elsewhere Site", boundary_geojson=OTHER_POLYGON_GEOJSON)
    pe = _user(db, company, "pe@trackco.com")
    se = _user(db, company, "se@trackco.com")
    emp = _user(db, company, "emp@trackco.com")
    make_assignment(db, company=company, project=shared_project, user=pe, role=AssignmentRole.PROJECT_ENGINEER)
    make_assignment(db, company=company, project=shared_project, user=se, role=AssignmentRole.SITE_ENGINEER)
    make_assignment(db, company=company, project=other_project, user=emp, role=AssignmentRole.EMPLOYEE)
    db.commit()

    headers = auth_header(client, email="pe@trackco.com", password="password123")
    resp = client.get("/api/v1/locations/team", headers=headers)
    assert resp.status_code == 200
    names = {row["full_name"] for row in resp.json()["data"]}
    assert "Se" in names
    assert "Emp" not in names
