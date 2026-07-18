"""Milestone 5: issue categories/priorities, auto-recorded status history,
comments, photos, and visibility scoping."""
from __future__ import annotations

import pytest

from app.models.enums import AssignmentRole, Role
from app.models.user import User
from tests.factories import (
    auth_header,
    make_assignment,
    make_company,
    make_issue,
    make_project,
    make_user,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def company(db):
    c = make_company(db, name="Issueco", slug="issueco")
    make_user(db, company=c, email="owner@issueco.com", role=Role.COMPANY_OWNER)
    make_user(db, company=c, email="hr@issueco.com", role=Role.HR_ADMIN)
    make_user(db, company=c, email="pe@issueco.com", role=Role.PROJECT_ENGINEER)
    make_user(db, company=c, email="emp@issueco.com", role=Role.EMPLOYEE)
    return c


def _user(db, company, email: str) -> User:
    return db.query(User).filter_by(company_id=company.id, email=email).one()


def test_employee_can_create_issue(client, company, db):
    project = make_project(db, company=company, name="Site A")
    db.commit()
    headers = auth_header(client, email="emp@issueco.com", password="password123")
    resp = client.post(
        "/api/v1/issues",
        headers=headers,
        json={"project_id": str(project.id), "title": "Rebar shortage", "category": "worker_shortage"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["status"] == "open"
    assert data["category"] == "worker_shortage"
    assert data["priority"] == "medium"


def test_hr_cannot_create_or_view_issues(client, company, db):
    project = make_project(db, company=company, name="Site B")
    db.commit()
    headers = auth_header(client, email="hr@issueco.com", password="password123")
    assert client.post(
        "/api/v1/issues",
        headers=headers,
        json={"project_id": str(project.id), "title": "Nope", "category": "other"},
    ).status_code == 403
    assert client.get("/api/v1/issues", headers=headers).status_code == 403


def test_employee_cannot_update_issue(client, company, db):
    project = make_project(db, company=company, name="Site C")
    emp = _user(db, company, "emp@issueco.com")
    issue = make_issue(db, company=company, project=project, title="Weather delay", reported_by=emp)
    db.commit()
    headers = auth_header(client, email="emp@issueco.com", password="password123")
    resp = client.patch(f"/api/v1/issues/{issue.id}", headers=headers, json={"status": "assigned"})
    assert resp.status_code == 403


def test_status_change_recorded_in_history_with_note(client, company, db):
    project = make_project(db, company=company, name="Site D")
    pe = _user(db, company, "pe@issueco.com")
    emp = _user(db, company, "emp@issueco.com")
    make_assignment(db, company=company, project=project, user=pe, role=AssignmentRole.PROJECT_ENGINEER)
    issue = make_issue(db, company=company, project=project, title="Quality issue", reported_by=emp)
    db.commit()
    headers = auth_header(client, email="pe@issueco.com", password="password123")

    resp = client.patch(
        f"/api/v1/issues/{issue.id}",
        headers=headers,
        json={"status": "assigned", "assigned_to_user_id": str(pe.id), "note": "Taking a look."},
    )
    assert resp.status_code == 200, resp.text

    history = client.get(f"/api/v1/issues/{issue.id}/history", headers=headers).json()["data"]
    # Entry 0: creation (from_status null -> open). Entry 1: open -> assigned.
    assert len(history) == 2
    assert history[0]["from_status"] is None
    assert history[0]["to_status"] == "open"
    assert history[1]["from_status"] == "open"
    assert history[1]["to_status"] == "assigned"
    assert history[1]["note"] == "Taking a look."


def test_resolved_at_set_and_cleared(client, company, db):
    project = make_project(db, company=company, name="Site E")
    pe = _user(db, company, "pe@issueco.com")
    make_assignment(db, company=company, project=project, user=pe, role=AssignmentRole.PROJECT_ENGINEER)
    issue = make_issue(db, company=company, project=project, title="Access blocked")
    db.commit()
    headers = auth_header(client, email="pe@issueco.com", password="password123")

    resolved = client.patch(f"/api/v1/issues/{issue.id}", headers=headers, json={"status": "resolved"})
    assert resolved.json()["data"]["resolved_at"] is not None

    reopened = client.patch(f"/api/v1/issues/{issue.id}", headers=headers, json={"status": "reopened"})
    assert reopened.json()["data"]["resolved_at"] is None


def test_employee_sees_only_own_reported_or_assigned_issues(client, company, db):
    project = make_project(db, company=company, name="Site F")
    emp = _user(db, company, "emp@issueco.com")
    pe = _user(db, company, "pe@issueco.com")
    make_assignment(db, company=company, project=project, user=emp)
    mine = make_issue(db, company=company, project=project, title="Mine", reported_by=emp)
    make_issue(db, company=company, project=project, title="Not mine", reported_by=pe)
    db.commit()
    headers = auth_header(client, email="emp@issueco.com", password="password123")

    resp = client.get("/api/v1/issues", headers=headers)
    titles = {i["title"] for i in resp.json()["data"]}
    assert titles == {"Mine"}
    assert client.get(f"/api/v1/issues/{mine.id}", headers=headers).status_code == 200


def test_pe_sees_all_issues_in_visible_project(client, company, db):
    project = make_project(db, company=company, name="Site G")
    pe = _user(db, company, "pe@issueco.com")
    emp = _user(db, company, "emp@issueco.com")
    make_assignment(db, company=company, project=project, user=pe, role=AssignmentRole.PROJECT_ENGINEER)
    make_issue(db, company=company, project=project, title="Issue 1", reported_by=emp)
    make_issue(db, company=company, project=project, title="Issue 2", reported_by=emp)
    db.commit()
    headers = auth_header(client, email="pe@issueco.com", password="password123")
    resp = client.get("/api/v1/issues", headers=headers)
    titles = {i["title"] for i in resp.json()["data"]}
    assert titles == {"Issue 1", "Issue 2"}


def test_issue_comments_and_photos(client, company, db):
    project = make_project(db, company=company, name="Site H")
    emp = _user(db, company, "emp@issueco.com")
    make_assignment(db, company=company, project=project, user=emp)
    issue = make_issue(db, company=company, project=project, title="Issue with comments", reported_by=emp)
    db.commit()
    headers = auth_header(client, email="emp@issueco.com", password="password123")

    comment_resp = client.post(
        f"/api/v1/issues/{issue.id}/comments", headers=headers, json={"body": "Still ongoing."}
    )
    assert comment_resp.status_code == 201, comment_resp.text
    assert len(client.get(f"/api/v1/issues/{issue.id}/comments", headers=headers).json()["data"]) == 1

    photo_resp = client.post(
        f"/api/v1/issues/{issue.id}/photos",
        headers=headers,
        json={"photo_url": "https://example.com/issue.jpg"},
    )
    assert photo_resp.status_code == 201, photo_resp.text
    assert len(client.get(f"/api/v1/issues/{issue.id}/photos", headers=headers).json()["data"]) == 1


def test_issue_isolated_across_companies(client, db):
    acme = make_company(db, name="Acme6", slug="acme6")
    globex = make_company(db, name="Globex6", slug="globex6")
    make_user(db, company=acme, email="owner@acme6.com", role=Role.COMPANY_OWNER)
    globex_project = make_project(db, company=globex, name="Globex Site")
    globex_issue = make_issue(db, company=globex, project=globex_project, title="Globex Issue")
    db.commit()

    headers = auth_header(client, email="owner@acme6.com", password="password123")
    resp = client.get(f"/api/v1/issues/{globex_issue.id}", headers=headers)
    assert resp.status_code == 404
