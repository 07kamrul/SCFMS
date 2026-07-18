"""Milestone 5: task workflow, comments, photos, overdue detection, visibility."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.enums import AssignmentRole, Role, TaskStatus
from app.models.user import User
from tests.factories import (
    auth_header,
    make_assignment,
    make_company,
    make_project,
    make_task,
    make_user,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def company(db):
    c = make_company(db, name="Taskco", slug="taskco")
    make_user(db, company=c, email="owner@taskco.com", role=Role.COMPANY_OWNER)
    make_user(db, company=c, email="hr@taskco.com", role=Role.HR_ADMIN)
    make_user(db, company=c, email="pe@taskco.com", role=Role.PROJECT_ENGINEER)
    make_user(db, company=c, email="se@taskco.com", role=Role.SITE_ENGINEER)
    make_user(db, company=c, email="emp@taskco.com", role=Role.EMPLOYEE)
    return c


def _user(db, company, email: str) -> User:
    return db.query(User).filter_by(company_id=company.id, email=email).one()


def test_pe_can_create_task(client, company, db):
    project = make_project(db, company=company, name="Site A")
    emp = _user(db, company, "emp@taskco.com")
    make_assignment(db, company=company, project=project, user=_user(db, company, "pe@taskco.com"), role=AssignmentRole.PROJECT_ENGINEER)
    db.commit()
    headers = auth_header(client, email="pe@taskco.com", password="password123")
    resp = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"project_id": str(project.id), "title": "Pour foundation", "assigned_to_user_id": str(emp.id)},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["title"] == "Pour foundation"
    assert data["status"] == "todo"
    assert data["priority"] == "medium"
    assert data["is_overdue"] is False


def test_hr_cannot_create_or_view_tasks(client, company, db):
    project = make_project(db, company=company, name="Site B")
    db.commit()
    headers = auth_header(client, email="hr@taskco.com", password="password123")
    assert client.post(
        "/api/v1/tasks", headers=headers, json={"project_id": str(project.id), "title": "Nope"}
    ).status_code == 403
    assert client.get("/api/v1/tasks", headers=headers).status_code == 403


def test_employee_cannot_create_task(client, company, db):
    project = make_project(db, company=company, name="Site C")
    db.commit()
    headers = auth_header(client, email="emp@taskco.com", password="password123")
    resp = client.post(
        "/api/v1/tasks", headers=headers, json={"project_id": str(project.id), "title": "Nope"}
    )
    assert resp.status_code == 403


def test_employee_can_update_own_task_status_but_not_approve(client, company, db):
    project = make_project(db, company=company, name="Site D")
    emp = _user(db, company, "emp@taskco.com")
    make_assignment(db, company=company, project=project, user=emp)
    task = make_task(db, company=company, project=project, title="Dig trench", assigned_to=emp)
    db.commit()
    headers = auth_header(client, email="emp@taskco.com", password="password123")

    resp = client.patch(f"/api/v1/tasks/{task.id}", headers=headers, json={"status": "in_progress"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "in_progress"

    resp2 = client.patch(f"/api/v1/tasks/{task.id}", headers=headers, json={"status": "approved"})
    assert resp2.status_code == 403


def test_employee_cannot_reassign_task(client, company, db):
    project = make_project(db, company=company, name="Site E")
    emp = _user(db, company, "emp@taskco.com")
    se = _user(db, company, "se@taskco.com")
    make_assignment(db, company=company, project=project, user=emp)
    task = make_task(db, company=company, project=project, title="Wire panel", assigned_to=emp)
    db.commit()
    headers = auth_header(client, email="emp@taskco.com", password="password123")
    resp = client.patch(
        f"/api/v1/tasks/{task.id}", headers=headers, json={"assigned_to_user_id": str(se.id)}
    )
    assert resp.status_code == 403


def test_pe_can_approve_and_reassign(client, company, db):
    project = make_project(db, company=company, name="Site F")
    pe = _user(db, company, "pe@taskco.com")
    emp = _user(db, company, "emp@taskco.com")
    se = _user(db, company, "se@taskco.com")
    make_assignment(db, company=company, project=project, user=pe, role=AssignmentRole.PROJECT_ENGINEER)
    task = make_task(db, company=company, project=project, title="Review plans", status=TaskStatus.SUBMITTED, assigned_to=emp)
    db.commit()
    headers = auth_header(client, email="pe@taskco.com", password="password123")

    resp = client.patch(f"/api/v1/tasks/{task.id}", headers=headers, json={"status": "approved"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "approved"

    resp2 = client.patch(
        f"/api/v1/tasks/{task.id}", headers=headers, json={"assigned_to_user_id": str(se.id)}
    )
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["data"]["assigned_to_user_id"] == str(se.id)


def test_employee_sees_only_own_tasks(client, company, db):
    project = make_project(db, company=company, name="Site G")
    emp = _user(db, company, "emp@taskco.com")
    se = _user(db, company, "se@taskco.com")
    make_assignment(db, company=company, project=project, user=emp)
    mine = make_task(db, company=company, project=project, title="My task", assigned_to=emp)
    make_task(db, company=company, project=project, title="Someone else's task", assigned_to=se)
    db.commit()
    headers = auth_header(client, email="emp@taskco.com", password="password123")

    resp = client.get("/api/v1/tasks", headers=headers)
    titles = {t["title"] for t in resp.json()["data"]}
    assert titles == {"My task"}
    assert client.get(f"/api/v1/tasks/{mine.id}", headers=headers).status_code == 200


def test_pe_sees_all_tasks_in_visible_project(client, company, db):
    project = make_project(db, company=company, name="Site H")
    pe = _user(db, company, "pe@taskco.com")
    emp = _user(db, company, "emp@taskco.com")
    se = _user(db, company, "se@taskco.com")
    make_assignment(db, company=company, project=project, user=pe, role=AssignmentRole.PROJECT_ENGINEER)
    make_task(db, company=company, project=project, title="Task 1", assigned_to=emp)
    make_task(db, company=company, project=project, title="Task 2", assigned_to=se)
    db.commit()
    headers = auth_header(client, email="pe@taskco.com", password="password123")
    resp = client.get("/api/v1/tasks", headers=headers)
    titles = {t["title"] for t in resp.json()["data"]}
    assert titles == {"Task 1", "Task 2"}


def test_overdue_detection(client, company, db):
    project = make_project(db, company=company, name="Site I")
    pe = _user(db, company, "pe@taskco.com")
    make_assignment(db, company=company, project=project, user=pe, role=AssignmentRole.PROJECT_ENGINEER)
    past = datetime.now(timezone.utc) - timedelta(days=2)
    overdue_task = make_task(db, company=company, project=project, title="Late task", due_date=past)
    make_task(
        db, company=company, project=project, title="Late but done", due_date=past, status=TaskStatus.COMPLETED
    )
    db.commit()
    headers = auth_header(client, email="pe@taskco.com", password="password123")

    get_resp = client.get(f"/api/v1/tasks/{overdue_task.id}", headers=headers)
    assert get_resp.json()["data"]["is_overdue"] is True

    filtered = client.get("/api/v1/tasks", headers=headers, params={"overdue": "true"})
    titles = {t["title"] for t in filtered.json()["data"]}
    assert titles == {"Late task"}


def test_task_comments_and_photos(client, company, db):
    project = make_project(db, company=company, name="Site J")
    emp = _user(db, company, "emp@taskco.com")
    make_assignment(db, company=company, project=project, user=emp)
    task = make_task(db, company=company, project=project, title="Task with comments", assigned_to=emp)
    db.commit()
    headers = auth_header(client, email="emp@taskco.com", password="password123")

    comment_resp = client.post(
        f"/api/v1/tasks/{task.id}/comments", headers=headers, json={"body": "Started this today."}
    )
    assert comment_resp.status_code == 201, comment_resp.text
    list_resp = client.get(f"/api/v1/tasks/{task.id}/comments", headers=headers)
    assert len(list_resp.json()["data"]) == 1

    photo_resp = client.post(
        f"/api/v1/tasks/{task.id}/photos",
        headers=headers,
        json={"photo_url": "https://example.com/photo.jpg", "caption": "Progress shot"},
    )
    assert photo_resp.status_code == 201, photo_resp.text
    photos = client.get(f"/api/v1/tasks/{task.id}/photos", headers=headers)
    assert len(photos.json()["data"]) == 1


def test_task_isolated_across_companies(client, db):
    acme = make_company(db, name="Acme5", slug="acme5")
    globex = make_company(db, name="Globex5", slug="globex5")
    make_user(db, company=acme, email="owner@acme5.com", role=Role.COMPANY_OWNER)
    globex_project = make_project(db, company=globex, name="Globex Site")
    globex_task = make_task(db, company=globex, project=globex_project, title="Globex Task")
    db.commit()

    headers = auth_header(client, email="owner@acme5.com", password="password123")
    resp = client.get(f"/api/v1/tasks/{globex_task.id}", headers=headers)
    assert resp.status_code == 404
