"""Seed a demo company with one user per role for local development.

Idempotent: re-running updates passwords but does not duplicate rows.
Run:  python seed.py   (with a migrated database and .env in place)
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.assignment import Assignment
from app.models.company import Company, CompanySettings
from app.models.enums import (
    AssignmentRole,
    IssueCategory,
    IssuePriority,
    ProjectStatus,
    Role,
    TaskPriority,
    TaskStatus,
    UserStatus,
)
from app.models.issue import Issue
from app.models.issue_status_history import IssueStatusHistory
from app.models.location_point import LocationPoint
from app.models.progress_photo import ProgressPhoto
from app.models.progress_report import DailyProgressReport
from app.models.progress_report_stage_entry import ProgressReportStageEntry
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.utils.geo import geojson_polygon_to_wkb, latlng_to_point_wkb

DEMO_SLUG = "demo-construction"

DEMO_USERS = [
    ("Olivia Owner", "owner@demo.com", "+8801711000001", Role.COMPANY_OWNER, "owner123"),
    ("Hina HR", "hr@demo.com", "+8801711000002", Role.HR_ADMIN, "hr123456"),
    ("Peter PE", "pe@demo.com", "+8801711000003", Role.PROJECT_ENGINEER, "pe123456"),
    ("Sara SE", "se@demo.com", "+8801711000004", Role.SITE_ENGINEER, "se123456"),
    ("Emil Employee", "emp@demo.com", "+8801711000005", Role.EMPLOYEE, "emp12345"),
]

_RIVERSIDE_BOUNDARY = {
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

DEMO_PROJECTS = [
    (
        "Riverside Tower",
        "12-storey mixed-use tower on the riverside plot.",
        ProjectStatus.RUNNING,
        45,
        _RIVERSIDE_BOUNDARY,
    ),
    ("Greenfield Warehouse", "Single-storey logistics warehouse.", ProjectStatus.PLANNED, 0, None),
    (
        "Lakeview Villas — Phase 1",
        "8-unit villa complex, phase 1 of 3.",
        ProjectStatus.COMPLETED,
        100,
        None,
    ),
]

# (project name, assignee email, assignment role)
DEMO_ASSIGNMENTS = [
    ("Riverside Tower", "pe@demo.com", AssignmentRole.PROJECT_ENGINEER),
    ("Riverside Tower", "se@demo.com", AssignmentRole.SITE_ENGINEER),
    ("Greenfield Warehouse", "emp@demo.com", AssignmentRole.EMPLOYEE),
]

# (assignee email, lat, lng) — demonstrates INSIDE_ASSIGNED / NEAR_ASSIGNED.
# emp@demo.com deliberately has no point, demonstrating UNKNOWN status.
DEMO_LOCATIONS = [
    ("se@demo.com", 23.8108, 90.4130),  # center of Riverside Tower -> inside_assigned
    ("pe@demo.com", 23.8108, 90.4140),  # ~45m east of the boundary -> near_assigned
]

# (project name, title, assignee email, status, priority)
DEMO_TASKS = [
    ("Riverside Tower", "Pour foundation slab", "se@demo.com", TaskStatus.IN_PROGRESS, TaskPriority.HIGH),
    ("Riverside Tower", "Submit structural drawings", "pe@demo.com", TaskStatus.SUBMITTED, TaskPriority.MEDIUM),
    ("Greenfield Warehouse", "Site survey", "emp@demo.com", TaskStatus.TODO, TaskPriority.LOW),
]

# (project name, title, category, reporter email, priority)
DEMO_ISSUES = [
    ("Riverside Tower", "Rebar delivery delayed", IssueCategory.WORK_DELAY, "se@demo.com", IssuePriority.HIGH),
    (
        "Greenfield Warehouse",
        "Access road blocked by flooding",
        IssueCategory.SITE_ACCESS_PROBLEM,
        "emp@demo.com",
        IssuePriority.CRITICAL,
    ),
]


def seed() -> None:
    db = SessionLocal()
    try:
        company = (
            db.query(Company).filter(Company.slug == DEMO_SLUG).one_or_none()
        )
        if company is None:
            company = Company(name="Demo Construction Co.", slug=DEMO_SLUG, is_active=True)
            db.add(company)
            db.flush()
            db.add(CompanySettings(company_id=company.id))
            print(f"Created company {company.name} ({company.id})")

        users_by_email: dict[str, User] = {}
        for full_name, email, phone, role, password in DEMO_USERS:
            user = (
                db.query(User)
                .filter(User.company_id == company.id, User.email == email)
                .one_or_none()
            )
            if user is None:
                user = User(
                    company_id=company.id,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    hashed_password=hash_password(password),
                    role=role,
                    status=UserStatus.ACTIVE,
                    is_identity_verified=True,
                )
                db.add(user)
                db.flush()
                print(f"  + {role.value:18} {email}  (password: {password})")
            else:
                user.hashed_password = hash_password(password)
                print(f"  ~ {role.value:18} {email}  (password reset)")
            users_by_email[email] = user

        projects_by_name: dict[str, Project] = {}
        for name, description, status, progress_percent, boundary_geojson in DEMO_PROJECTS:
            project = (
                db.query(Project)
                .filter(Project.company_id == company.id, Project.name == name)
                .one_or_none()
            )
            if project is None:
                project = Project(
                    company_id=company.id,
                    name=name,
                    description=description,
                    status=status,
                    progress_percent=progress_percent,
                    boundary=geojson_polygon_to_wkb(boundary_geojson) if boundary_geojson else None,
                )
                db.add(project)
                db.flush()
                print(f"  + project {name!r} ({status.value}, {progress_percent}%)")
            projects_by_name[name] = project

        owner = users_by_email["owner@demo.com"]
        for project_name, email, role in DEMO_ASSIGNMENTS:
            project = projects_by_name[project_name]
            user = users_by_email[email]
            existing = (
                db.query(Assignment)
                .filter(
                    Assignment.project_id == project.id,
                    Assignment.user_id == user.id,
                    Assignment.ended_at.is_(None),
                )
                .one_or_none()
            )
            if existing is None:
                db.add(
                    Assignment(
                        company_id=company.id,
                        project_id=project.id,
                        user_id=user.id,
                        role=role,
                        assigned_by_user_id=owner.id,
                    )
                )
                print(f"  + assignment {email} -> {project_name!r} ({role.value})")

        now = datetime.now(timezone.utc)
        for email, lat, lng in DEMO_LOCATIONS:
            user = users_by_email[email]
            point = (
                db.query(LocationPoint)
                .filter(LocationPoint.user_id == user.id)
                .order_by(LocationPoint.recorded_at.desc())
                .first()
            )
            if point is None:
                db.add(
                    LocationPoint(
                        company_id=company.id,
                        user_id=user.id,
                        point=latlng_to_point_wkb(lat, lng),
                        recorded_at=now,
                    )
                )
                print(f"  + location point for {email} ({lat}, {lng})")
            else:
                point.point = latlng_to_point_wkb(lat, lng)
                point.recorded_at = now
                print(f"  ~ location point for {email} refreshed to now")

        for project_name, title, email, status, priority in DEMO_TASKS:
            project = projects_by_name[project_name]
            assignee = users_by_email[email]
            existing = (
                db.query(Task)
                .filter(Task.project_id == project.id, Task.title == title)
                .one_or_none()
            )
            if existing is None:
                db.add(
                    Task(
                        company_id=company.id,
                        project_id=project.id,
                        title=title,
                        status=status,
                        priority=priority,
                        assigned_to_user_id=assignee.id,
                        created_by_user_id=owner.id,
                    )
                )
                print(f"  + task {title!r} -> {email} ({status.value})")

        for project_name, title, category, email, priority in DEMO_ISSUES:
            project = projects_by_name[project_name]
            reporter = users_by_email[email]
            existing = (
                db.query(Issue)
                .filter(Issue.project_id == project.id, Issue.title == title)
                .one_or_none()
            )
            if existing is None:
                issue = Issue(
                    company_id=company.id,
                    project_id=project.id,
                    title=title,
                    category=category,
                    priority=priority,
                    reported_by_user_id=reporter.id,
                )
                db.add(issue)
                db.flush()
                db.add(
                    IssueStatusHistory(
                        company_id=company.id,
                        issue_id=issue.id,
                        from_status=None,
                        to_status=issue.status,
                        changed_by_user_id=reporter.id,
                    )
                )
                print(f"  + issue {title!r} reported by {email} ({category.value})")

        riverside = projects_by_name["Riverside Tower"]
        se = users_by_email["se@demo.com"]
        today = now.date()
        report = (
            db.query(DailyProgressReport)
            .filter(
                DailyProgressReport.project_id == riverside.id,
                DailyProgressReport.report_date == today,
                DailyProgressReport.submitted_by_user_id == se.id,
            )
            .one_or_none()
        )
        if report is None:
            report = DailyProgressReport(
                company_id=company.id,
                project_id=riverside.id,
                submitted_by_user_id=se.id,
                report_date=today,
                summary="Foundation work complete, framing underway on the east wing.",
                overall_progress_percent=45,
            )
            db.add(report)
            db.flush()
            db.add_all(
                [
                    ProgressReportStageEntry(
                        company_id=company.id,
                        report_id=report.id,
                        stage_name="Foundation",
                        progress_percent=100,
                    ),
                    ProgressReportStageEntry(
                        company_id=company.id,
                        report_id=report.id,
                        stage_name="Framing",
                        progress_percent=20,
                        notes="Started east wing columns.",
                    ),
                ]
            )
            db.add(
                ProgressPhoto(
                    company_id=company.id,
                    project_id=riverside.id,
                    report_id=report.id,
                    user_id=se.id,
                    photo_url="https://example.com/demo/riverside-day1.jpg",
                    caption="East wing framing progress",
                )
            )
            riverside.progress_percent = 45
            print(f"  + progress report for {riverside.name!r} on {today} (45%, 2 stages, 1 photo)")

        db.commit()
        print("\nSeed complete. Log in with any credential above.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
