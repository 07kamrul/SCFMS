"""Milestone 2: projects, their GIS boundary, and view-scope permissions."""
from __future__ import annotations

import pytest

from app.models.enums import AssignmentRole, ProjectStatus, Role
from app.models.user import User
from tests.factories import (
    SAMPLE_POLYGON_GEOJSON,
    auth_header,
    make_assignment,
    make_company,
    make_project,
    make_user,
)

pytestmark = pytest.mark.integration

_SELF_INTERSECTING_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[[0, 0], [10, 10], [10, 0], [0, 10], [0, 0]]],
}


@pytest.fixture
def company(db):
    c = make_company(db, name="Buildco", slug="buildco-projects")
    make_user(db, company=c, email="owner@buildco.com", role=Role.COMPANY_OWNER)
    make_user(db, company=c, email="hr@buildco.com", role=Role.HR_ADMIN)
    make_user(db, company=c, email="pe@buildco.com", role=Role.PROJECT_ENGINEER)
    make_user(db, company=c, email="emp@buildco.com", role=Role.EMPLOYEE)
    return c


def test_owner_can_create_project_with_boundary(client, company):
    headers = auth_header(client, email="owner@buildco.com", password="password123")
    resp = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Riverside Tower", "boundary": SAMPLE_POLYGON_GEOJSON},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["name"] == "Riverside Tower"
    assert data["status"] == "planned"
    assert data["boundary"]["type"] == "Polygon"
    assert data["boundary"]["coordinates"] == SAMPLE_POLYGON_GEOJSON["coordinates"]


def test_employee_cannot_create_project(client, company):
    headers = auth_header(client, email="emp@buildco.com", password="password123")
    resp = client.post("/api/v1/projects", headers=headers, json={"name": "Nope"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "permission_denied"


def test_create_project_rejects_unclosed_ring(client, company):
    headers = auth_header(client, email="owner@buildco.com", password="password123")
    bad = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]}
    resp = client.post(
        "/api/v1/projects", headers=headers, json={"name": "Bad Ring", "boundary": bad}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_create_project_rejects_self_intersecting_polygon(client, company):
    headers = auth_header(client, email="owner@buildco.com", password="password123")
    resp = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Bowtie", "boundary": _SELF_INTERSECTING_GEOJSON},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_progress_percent_out_of_range_rejected(client, company, db):
    project = make_project(db, company=company, name="Existing")
    db.commit()
    headers = auth_header(client, email="owner@buildco.com", password="password123")
    resp = client.patch(
        f"/api/v1/projects/{project.id}", headers=headers, json={"progress_percent": 150}
    )
    assert resp.status_code == 422


def test_archive_sets_status_archived(client, company, db):
    project = make_project(db, company=company, name="To Archive", status=ProjectStatus.RUNNING)
    db.commit()
    headers = auth_header(client, email="owner@buildco.com", password="password123")
    resp = client.post(f"/api/v1/projects/{project.id}/archive", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "archived"


def test_map_endpoint_returns_boundary_geojson(client, company, db):
    make_project(db, company=company, name="With Boundary", boundary_geojson=SAMPLE_POLYGON_GEOJSON)
    make_project(db, company=company, name="Without Boundary")
    db.commit()
    headers = auth_header(client, email="owner@buildco.com", password="password123")
    resp = client.get("/api/v1/projects/map", headers=headers)
    assert resp.status_code == 200
    by_name = {p["name"]: p for p in resp.json()["data"]}
    assert by_name["With Boundary"]["boundary"]["coordinates"] == SAMPLE_POLYGON_GEOJSON["coordinates"]
    assert by_name["Without Boundary"]["boundary"] is None


def test_hr_admin_can_view_all_but_not_create(client, company, db):
    make_project(db, company=company, name="Visible To HR")
    db.commit()
    headers = auth_header(client, email="hr@buildco.com", password="password123")
    assert client.get("/api/v1/projects", headers=headers).status_code == 200
    resp = client.post("/api/v1/projects", headers=headers, json={"name": "Nope"})
    assert resp.status_code == 403


def test_view_assigned_role_sees_only_its_assigned_projects(client, company, db):
    """PROJECT_ENGINEER only has PROJECT_VIEW_ASSIGNED — Milestone 3's real
    assignment data now drives this scoping (see ProjectService.list())."""
    pe = db.query(User).filter_by(company_id=company.id, email="pe@buildco.com").one()
    assigned_project = make_project(db, company=company, name="Assigned To PE")
    other_project = make_project(db, company=company, name="Not Assigned")
    make_assignment(db, company=company, project=assigned_project, user=pe, role=AssignmentRole.PROJECT_ENGINEER)
    db.commit()
    headers = auth_header(client, email="pe@buildco.com", password="password123")

    list_resp = client.get("/api/v1/projects", headers=headers)
    assert list_resp.status_code == 200
    names = {p["name"] for p in list_resp.json()["data"]}
    assert names == {"Assigned To PE"}

    map_resp = client.get("/api/v1/projects/map", headers=headers)
    assert {p["name"] for p in map_resp.json()["data"]} == {"Assigned To PE"}

    assert client.get(f"/api/v1/projects/{assigned_project.id}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/projects/{other_project.id}", headers=headers).status_code == 404


def test_view_assigned_role_sees_nothing_without_an_assignment(client, company, db):
    project = make_project(db, company=company, name="Unassigned Project")
    db.commit()
    headers = auth_header(client, email="pe@buildco.com", password="password123")

    list_resp = client.get("/api/v1/projects", headers=headers)
    assert list_resp.json()["data"] == []
    assert list_resp.json()["meta"]["total"] == 0
    assert client.get("/api/v1/projects/map", headers=headers).json()["data"] == []
    assert client.get(f"/api/v1/projects/{project.id}", headers=headers).status_code == 404


def test_project_isolated_across_companies(client, db):
    acme = make_company(db, name="Acme3", slug="acme3")
    globex = make_company(db, name="Globex3", slug="globex3")
    make_user(db, company=acme, email="owner@acme3.com", role=Role.COMPANY_OWNER)
    globex_project = make_project(db, company=globex, name="Globex Secret Site")
    db.commit()

    headers = auth_header(client, email="owner@acme3.com", password="password123")
    resp = client.get(f"/api/v1/projects/{globex_project.id}", headers=headers)
    assert resp.status_code == 404

    list_resp = client.get("/api/v1/projects", headers=headers)
    names = {p["name"] for p in list_resp.json()["data"]}
    assert "Globex Secret Site" not in names


def test_owner_can_delete_project(client, company, db):
    project = make_project(db, company=company, name="Delete Me")
    db.commit()
    headers = auth_header(client, email="owner@buildco.com", password="password123")
    resp = client.delete(f"/api/v1/projects/{project.id}", headers=headers)
    assert resp.status_code == 200
    assert client.get(f"/api/v1/projects/{project.id}", headers=headers).status_code == 404
