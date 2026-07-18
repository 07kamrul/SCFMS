"""Small helpers to build companies, users, and projects in tests."""
from __future__ import annotations

from datetime import date as date_
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.assignment import Assignment
from app.models.company import Company, CompanySettings
from app.models.enums import (
    AssignmentRole,
    IssueCategory,
    IssuePriority,
    IssueStatus,
    ProjectStatus,
    Role,
    TaskPriority,
    TaskStatus,
    UserStatus,
)
from app.models.issue import Issue
from app.models.issue_status_history import IssueStatusHistory
from app.models.location_point import LocationPoint
from app.models.progress_report import DailyProgressReport
from app.models.progress_report_stage_entry import ProgressReportStageEntry
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.utils.geo import geojson_polygon_to_wkb, latlng_to_point_wkb

SAMPLE_POLYGON_GEOJSON: dict[str, Any] = {
    "type": "Polygon",
    "coordinates": [
        [
            [90.4125, 23.8103],
            [90.4135, 23.8103],
            [90.4135, 23.8113],
            [90.4125, 23.8113],
            [90.4125, 23.8103],
        ]
    ],
}

# Coordinates relative to SAMPLE_POLYGON_GEOJSON's ~100m x 110m box.
INSIDE_LATLNG = (23.8108, 90.4130)  # center of the box
NEAR_LATLNG = (23.8108, 90.4140)  # ~45m east of the box's edge
FAR_LATLNG = (23.9000, 90.5000)  # many km away

# A second, non-overlapping project boundary ~10km east — for "wrong site" tests.
OTHER_POLYGON_GEOJSON: dict[str, Any] = {
    "type": "Polygon",
    "coordinates": [
        [
            [90.5125, 23.8103],
            [90.5135, 23.8103],
            [90.5135, 23.8113],
            [90.5125, 23.8113],
            [90.5125, 23.8103],
        ]
    ],
}
OTHER_INSIDE_LATLNG = (23.8108, 90.5130)


def make_company(db: Session, *, name: str, slug: str) -> Company:
    company = Company(name=name, slug=slug, is_active=True)
    db.add(company)
    db.flush()
    db.add(CompanySettings(company_id=company.id))
    db.flush()
    return company


def make_user(
    db: Session,
    *,
    company: Company,
    email: str,
    role: Role,
    password: str = "password123",
    phone: str | None = None,
    status: UserStatus = UserStatus.ACTIVE,
) -> User:
    user = User(
        company_id=company.id,
        full_name=email.split("@")[0].title(),
        email=email,
        phone=phone,
        hashed_password=hash_password(password),
        role=role,
        status=status,
    )
    db.add(user)
    db.flush()
    return user


def make_project(
    db: Session,
    *,
    company: Company,
    name: str,
    status: ProjectStatus = ProjectStatus.PLANNED,
    progress_percent: int = 0,
    boundary_geojson: dict[str, Any] | None = None,
) -> Project:
    project = Project(
        company_id=company.id,
        name=name,
        status=status,
        progress_percent=progress_percent,
        boundary=geojson_polygon_to_wkb(boundary_geojson) if boundary_geojson else None,
    )
    db.add(project)
    db.flush()
    return project


def make_assignment(
    db: Session,
    *,
    company: Company,
    project: Project,
    user: User,
    role: AssignmentRole = AssignmentRole.EMPLOYEE,
    assigned_by: User | None = None,
    ended_at=None,
) -> Assignment:
    assignment = Assignment(
        company_id=company.id,
        project_id=project.id,
        user_id=user.id,
        role=role,
        assigned_by_user_id=assigned_by.id if assigned_by else None,
        ended_at=ended_at,
    )
    db.add(assignment)
    db.flush()
    return assignment


def make_location_point(
    db: Session,
    *,
    company: Company,
    user: User,
    lat: float,
    lng: float,
    recorded_at: datetime | None = None,
    is_mock_location: bool = False,
) -> LocationPoint:
    point = LocationPoint(
        company_id=company.id,
        user_id=user.id,
        point=latlng_to_point_wkb(lat, lng),
        recorded_at=recorded_at or datetime.now(timezone.utc),
        is_mock_location=is_mock_location,
    )
    db.add(point)
    db.flush()
    return point


def make_task(
    db: Session,
    *,
    company: Company,
    project: Project,
    title: str,
    status: TaskStatus = TaskStatus.TODO,
    priority: TaskPriority = TaskPriority.MEDIUM,
    assigned_to: User | None = None,
    created_by: User | None = None,
    due_date: datetime | None = None,
) -> Task:
    task = Task(
        company_id=company.id,
        project_id=project.id,
        title=title,
        status=status,
        priority=priority,
        assigned_to_user_id=assigned_to.id if assigned_to else None,
        created_by_user_id=created_by.id if created_by else None,
        due_date=due_date,
    )
    db.add(task)
    db.flush()
    return task


def make_issue(
    db: Session,
    *,
    company: Company,
    project: Project,
    title: str,
    category: IssueCategory = IssueCategory.OTHER,
    priority: IssuePriority = IssuePriority.MEDIUM,
    status: IssueStatus = IssueStatus.OPEN,
    reported_by: User | None = None,
    assigned_to: User | None = None,
) -> Issue:
    issue = Issue(
        company_id=company.id,
        project_id=project.id,
        title=title,
        category=category,
        priority=priority,
        status=status,
        reported_by_user_id=reported_by.id if reported_by else None,
        assigned_to_user_id=assigned_to.id if assigned_to else None,
    )
    db.add(issue)
    db.flush()
    # Matches IssueService.create(), which always records a creation entry.
    db.add(
        IssueStatusHistory(
            company_id=company.id,
            issue_id=issue.id,
            from_status=None,
            to_status=issue.status,
            changed_by_user_id=reported_by.id if reported_by else None,
        )
    )
    db.flush()
    return issue


def make_progress_report(
    db: Session,
    *,
    company: Company,
    project: Project,
    submitted_by: User | None = None,
    report_date: date_ | None = None,
    summary: str | None = None,
    overall_progress_percent: int | None = None,
    stage_entries: list[tuple[str, int]] | None = None,
) -> DailyProgressReport:
    report = DailyProgressReport(
        company_id=company.id,
        project_id=project.id,
        submitted_by_user_id=submitted_by.id if submitted_by else None,
        report_date=report_date or date_.today(),
        summary=summary,
        overall_progress_percent=overall_progress_percent,
    )
    db.add(report)
    db.flush()
    for stage_name, progress_percent in stage_entries or []:
        db.add(
            ProgressReportStageEntry(
                company_id=company.id,
                report_id=report.id,
                stage_name=stage_name,
                progress_percent=progress_percent,
            )
        )
    db.flush()
    return report


def auth_header(client, *, email: str, password: str) -> dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["data"]["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
