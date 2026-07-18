"""Milestone 6: daily progress reports, stage entries, and photo timeline."""
from __future__ import annotations

from datetime import date

import pytest

from app.models.enums import AssignmentRole, Role
from app.models.user import User
from tests.factories import (
    auth_header,
    make_assignment,
    make_company,
    make_progress_report,
    make_project,
    make_user,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def company(db):
    c = make_company(db, name="Reportco", slug="reportco")
    make_user(db, company=c, email="owner@reportco.com", role=Role.COMPANY_OWNER)
    make_user(db, company=c, email="hr@reportco.com", role=Role.HR_ADMIN)
    make_user(db, company=c, email="pe@reportco.com", role=Role.PROJECT_ENGINEER)
    make_user(db, company=c, email="se@reportco.com", role=Role.SITE_ENGINEER)
    make_user(db, company=c, email="emp@reportco.com", role=Role.EMPLOYEE)
    return c


def _user(db, company, email: str) -> User:
    return db.query(User).filter_by(company_id=company.id, email=email).one()


def test_se_can_submit_report_and_it_updates_project_progress(client, company, db):
    project = make_project(db, company=company, name="Site A", progress_percent=10)
    se = _user(db, company, "se@reportco.com")
    make_assignment(db, company=company, project=project, user=se, role=AssignmentRole.SITE_ENGINEER)
    db.commit()
    headers = auth_header(client, email="se@reportco.com", password="password123")

    resp = client.post(
        "/api/v1/progress-reports",
        headers=headers,
        json={
            "project_id": str(project.id),
            "report_date": "2026-08-01",
            "summary": "Good progress today.",
            "overall_progress_percent": 35,
            "stage_entries": [
                {"stage_name": "Foundation", "progress_percent": 100},
                {"stage_name": "Framing", "progress_percent": 20, "notes": "Started east wing"},
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["overall_progress_percent"] == 35
    assert len(data["stage_entries"]) == 2
    assert {e["stage_name"] for e in data["stage_entries"]} == {"Foundation", "Framing"}

    db.refresh(project)
    assert project.progress_percent == 35


def test_pe_cannot_submit_report(client, company, db):
    project = make_project(db, company=company, name="Site B")
    db.commit()
    headers = auth_header(client, email="pe@reportco.com", password="password123")
    resp = client.post(
        "/api/v1/progress-reports",
        headers=headers,
        json={"project_id": str(project.id), "report_date": "2026-08-01"},
    )
    assert resp.status_code == 403


def test_hr_and_employee_cannot_view_reports(client, company, db):
    project = make_project(db, company=company, name="Site C")
    make_progress_report(db, company=company, project=project)
    db.commit()
    hr_headers = auth_header(client, email="hr@reportco.com", password="password123")
    emp_headers = auth_header(client, email="emp@reportco.com", password="password123")
    assert client.get("/api/v1/progress-reports", headers=hr_headers).status_code == 403
    assert client.get("/api/v1/progress-reports", headers=emp_headers).status_code == 403


def test_pe_can_view_reports_on_assigned_project(client, company, db):
    project = make_project(db, company=company, name="Site D")
    pe = _user(db, company, "pe@reportco.com")
    make_assignment(db, company=company, project=project, user=pe, role=AssignmentRole.PROJECT_ENGINEER)
    make_progress_report(db, company=company, project=project, summary="Day 1")
    db.commit()
    headers = auth_header(client, email="pe@reportco.com", password="password123")
    resp = client.get("/api/v1/progress-reports", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


def test_pe_cannot_view_reports_on_unassigned_project(client, company, db):
    project = make_project(db, company=company, name="Site E")
    make_progress_report(db, company=company, project=project)
    db.commit()
    headers = auth_header(client, email="pe@reportco.com", password="password123")
    resp = client.get("/api/v1/progress-reports", headers=headers)
    assert resp.json()["data"] == []


def test_report_isolated_across_companies(client, db):
    acme = make_company(db, name="Acme7", slug="acme7")
    globex = make_company(db, name="Globex7", slug="globex7")
    make_user(db, company=acme, email="owner@acme7.com", role=Role.COMPANY_OWNER)
    globex_project = make_project(db, company=globex, name="Globex Site")
    globex_report = make_progress_report(db, company=globex, project=globex_project)
    db.commit()

    headers = auth_header(client, email="owner@acme7.com", password="password123")
    resp = client.get(f"/api/v1/progress-reports/{globex_report.id}", headers=headers)
    assert resp.status_code == 404


def test_report_photo_create_and_list(client, company, db):
    project = make_project(db, company=company, name="Site F")
    se = _user(db, company, "se@reportco.com")
    make_assignment(db, company=company, project=project, user=se, role=AssignmentRole.SITE_ENGINEER)
    report = make_progress_report(db, company=company, project=project)
    db.commit()
    headers = auth_header(client, email="se@reportco.com", password="password123")

    resp = client.post(
        f"/api/v1/progress-reports/{report.id}/photos",
        headers=headers,
        json={"photo_url": "https://example.com/site.jpg", "caption": "East wing"},
    )
    assert resp.status_code == 201, resp.text
    photos = client.get(f"/api/v1/progress-reports/{report.id}/photos", headers=headers)
    assert len(photos.json()["data"]) == 1


def test_employee_cannot_upload_progress_photo_despite_having_photo_upload_permission(client, company, db):
    """Employee holds PHOTO_UPLOAD generally (for task/issue photos) but has
    no PROGRESS_VIEW at all — must not be able to attach progress photos."""
    project = make_project(db, company=company, name="Site G")
    emp = _user(db, company, "emp@reportco.com")
    make_assignment(db, company=company, project=project, user=emp)
    report = make_progress_report(db, company=company, project=project)
    db.commit()
    headers = auth_header(client, email="emp@reportco.com", password="password123")
    resp = client.post(
        f"/api/v1/progress-reports/{report.id}/photos",
        headers=headers,
        json={"photo_url": "https://example.com/sneaky.jpg"},
    )
    assert resp.status_code == 403


def test_project_photo_timeline_aggregates_across_reports(client, company, db):
    project = make_project(db, company=company, name="Site H")
    owner_headers = auth_header(client, email="owner@reportco.com", password="password123")
    report1 = make_progress_report(db, company=company, project=project, report_date=date(2026, 8, 1))
    report2 = make_progress_report(db, company=company, project=project, report_date=date(2026, 8, 2))
    db.commit()

    client.post(
        f"/api/v1/progress-reports/{report1.id}/photos",
        headers=owner_headers,
        json={"photo_url": "https://example.com/day1.jpg"},
    )
    client.post(
        f"/api/v1/progress-reports/{report2.id}/photos",
        headers=owner_headers,
        json={"photo_url": "https://example.com/day2.jpg"},
    )

    resp = client.get(
        "/api/v1/progress-reports/timeline", headers=owner_headers, params={"project_id": str(project.id)}
    )
    assert resp.status_code == 200
    urls = [p["photo_url"] for p in resp.json()["data"]]
    assert urls == ["https://example.com/day1.jpg", "https://example.com/day2.jpg"]
