"""Milestone 3: employee <-> project assignments and history-on-transfer."""
from __future__ import annotations

import pytest

from app.models.enums import AssignmentRole, Role
from app.models.user import User
from tests.factories import auth_header, make_assignment, make_company, make_project, make_user

pytestmark = pytest.mark.integration


@pytest.fixture
def company(db):
    c = make_company(db, name="Assignco", slug="assignco")
    make_user(db, company=c, email="owner@assignco.com", role=Role.COMPANY_OWNER)
    make_user(db, company=c, email="hr@assignco.com", role=Role.HR_ADMIN)
    make_user(db, company=c, email="pe@assignco.com", role=Role.PROJECT_ENGINEER)
    make_user(db, company=c, email="emp@assignco.com", role=Role.EMPLOYEE)
    return c


def _user(db, company, email: str) -> User:
    return db.query(User).filter_by(company_id=company.id, email=email).one()


def test_hr_can_assign_employee_to_project(client, company, db):
    project = make_project(db, company=company, name="Site A")
    emp = _user(db, company, "emp@assignco.com")
    db.commit()
    headers = auth_header(client, email="hr@assignco.com", password="password123")
    resp = client.post(
        "/api/v1/assignments",
        headers=headers,
        json={"project_id": str(project.id), "user_id": str(emp.id), "role": "employee"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["project_id"] == str(project.id)
    assert data["user_id"] == str(emp.id)
    assert data["ended_at"] is None


def test_project_engineer_cannot_manage_assignments(client, company, db):
    project = make_project(db, company=company, name="Site B")
    emp = _user(db, company, "emp@assignco.com")
    db.commit()
    headers = auth_header(client, email="pe@assignco.com", password="password123")
    resp = client.post(
        "/api/v1/assignments",
        headers=headers,
        json={"project_id": str(project.id), "user_id": str(emp.id), "role": "employee"},
    )
    assert resp.status_code == 403


def test_duplicate_active_assignment_rejected(client, company, db):
    project = make_project(db, company=company, name="Site C")
    emp = _user(db, company, "emp@assignco.com")
    make_assignment(db, company=company, project=project, user=emp)
    db.commit()
    headers = auth_header(client, email="hr@assignco.com", password="password123")
    resp = client.post(
        "/api/v1/assignments",
        headers=headers,
        json={"project_id": str(project.id), "user_id": str(emp.id), "role": "employee"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


def test_end_assignment(client, company, db):
    project = make_project(db, company=company, name="Site D")
    emp = _user(db, company, "emp@assignco.com")
    assignment = make_assignment(db, company=company, project=project, user=emp)
    db.commit()
    headers = auth_header(client, email="hr@assignco.com", password="password123")

    resp = client.post(f"/api/v1/assignments/{assignment.id}/end", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["ended_at"] is not None

    # Ending twice is rejected — it's already history.
    resp2 = client.post(f"/api/v1/assignments/{assignment.id}/end", headers=headers)
    assert resp2.status_code == 409


def test_transfer_preserves_history(client, company, db):
    old_project = make_project(db, company=company, name="Old Site")
    new_project = make_project(db, company=company, name="New Site")
    emp = _user(db, company, "emp@assignco.com")
    assignment = make_assignment(
        db, company=company, project=old_project, user=emp, role=AssignmentRole.EMPLOYEE
    )
    db.commit()
    headers = auth_header(client, email="hr@assignco.com", password="password123")

    resp = client.post(
        f"/api/v1/assignments/{assignment.id}/transfer",
        headers=headers,
        json={"new_project_id": str(new_project.id), "role": "site_engineer"},
    )
    assert resp.status_code == 200, resp.text
    new_row = resp.json()["data"]
    assert new_row["id"] != str(assignment.id)
    assert new_row["project_id"] == str(new_project.id)
    assert new_row["role"] == "site_engineer"
    assert new_row["ended_at"] is None

    # Old row is preserved as ended history, not deleted.
    history = client.get(
        "/api/v1/assignments", headers=headers, params={"user_id": str(emp.id)}
    ).json()["data"]
    by_project = {row["project_id"]: row for row in history}
    assert by_project[str(old_project.id)]["ended_at"] is not None
    assert by_project[str(new_project.id)]["ended_at"] is None
    assert len(history) == 2


def test_transfer_to_same_project_rejected(client, company, db):
    project = make_project(db, company=company, name="Site E")
    emp = _user(db, company, "emp@assignco.com")
    assignment = make_assignment(db, company=company, project=project, user=emp)
    db.commit()
    headers = auth_header(client, email="hr@assignco.com", password="password123")
    resp = client.post(
        f"/api/v1/assignments/{assignment.id}/transfer",
        headers=headers,
        json={"new_project_id": str(project.id), "role": "employee"},
    )
    assert resp.status_code == 409


def test_employee_can_see_own_assignments_without_assignment_view_permission(client, company, db):
    project = make_project(db, company=company, name="Site F")
    emp = _user(db, company, "emp@assignco.com")
    make_assignment(db, company=company, project=project, user=emp)
    db.commit()
    headers = auth_header(client, email="emp@assignco.com", password="password123")

    # Employee lacks ASSIGNMENT_VIEW, so the full roster is forbidden...
    assert client.get("/api/v1/assignments", headers=headers).status_code == 403
    # ...but /me is always available.
    resp = client.get("/api/v1/assignments/me", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1
    assert resp.json()["data"][0]["project_id"] == str(project.id)


def test_assignment_isolated_across_companies(client, db):
    acme = make_company(db, name="Acme4", slug="acme4")
    globex = make_company(db, name="Globex4", slug="globex4")
    make_user(db, company=acme, email="hr@acme4.com", role=Role.HR_ADMIN)
    globex_project = make_project(db, company=globex, name="Globex Site")
    globex_emp = make_user(db, company=globex, email="emp@globex4.com", role=Role.EMPLOYEE)
    db.commit()

    headers = auth_header(client, email="hr@acme4.com", password="password123")
    resp = client.post(
        "/api/v1/assignments",
        headers=headers,
        json={
            "project_id": str(globex_project.id),
            "user_id": str(globex_emp.id),
            "role": "employee",
        },
    )
    # Cross-tenant project id resolves to not-found, never leaks existence.
    assert resp.status_code == 404
