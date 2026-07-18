"""Model registry.

Importing every model here ensures they are all registered on `Base.metadata`
before Alembic autogenerate or `create_all` runs.
"""
from app.db.base import Base
from app.models.activity_log import ActivityLog
from app.models.assignment import Assignment
from app.models.company import Company, CompanySettings
from app.models.issue import Issue
from app.models.issue_comment import IssueComment
from app.models.issue_photo import IssuePhoto
from app.models.issue_status_history import IssueStatusHistory
from app.models.location_point import LocationPoint
from app.models.progress_photo import ProgressPhoto
from app.models.progress_report import DailyProgressReport
from app.models.progress_report_stage_entry import ProgressReportStageEntry
from app.models.project import Project
from app.models.refresh_token import RefreshToken
from app.models.task import Task
from app.models.task_comment import TaskComment
from app.models.task_photo import TaskPhoto
from app.models.user import User

__all__ = [
    "Base",
    "ActivityLog",
    "Assignment",
    "Company",
    "CompanySettings",
    "DailyProgressReport",
    "Issue",
    "IssueComment",
    "IssuePhoto",
    "IssueStatusHistory",
    "LocationPoint",
    "ProgressPhoto",
    "ProgressReportStageEntry",
    "Project",
    "RefreshToken",
    "Task",
    "TaskComment",
    "TaskPhoto",
    "User",
]
