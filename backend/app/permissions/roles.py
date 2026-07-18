"""Static role → permission matrix.

Roles are fixed by the product (5 total), so permissions are a code-defined
matrix rather than runtime-editable tables. This keeps checks fast and the
authorization model auditable in one place.
"""
from __future__ import annotations

import enum

from app.models.enums import Role


class Permission(str, enum.Enum):
    # Company / settings
    COMPANY_VIEW = "company:view"
    COMPANY_MANAGE_SETTINGS = "company:manage_settings"

    # Users / employees
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DEACTIVATE = "user:deactivate"
    USER_RESET_PASSWORD = "user:reset_password"
    USER_ASSIGN_ROLE = "user:assign_role"

    # Projects
    PROJECT_VIEW_ALL = "project:view_all"
    PROJECT_VIEW_ASSIGNED = "project:view_assigned"
    PROJECT_CREATE = "project:create"
    PROJECT_UPDATE = "project:update"
    PROJECT_ARCHIVE = "project:archive"
    PROJECT_DELETE = "project:delete"

    # Assignments
    ASSIGNMENT_VIEW = "assignment:view"
    ASSIGNMENT_MANAGE = "assignment:manage"

    # Tracking
    TRACKING_VIEW_ALL = "tracking:view_all"
    TRACKING_VIEW_ASSIGNED = "tracking:view_assigned"
    TRACKING_VIEW_SELF = "tracking:view_self"
    LOCATION_SHARE = "location:share"

    # Tasks
    TASK_CREATE = "task:create"
    TASK_UPDATE = "task:update"
    TASK_APPROVE = "task:approve"
    TASK_VIEW = "task:view"

    # Issues
    ISSUE_CREATE = "issue:create"
    ISSUE_UPDATE = "issue:update"
    ISSUE_VIEW = "issue:view"

    # Progress & photos
    PROGRESS_SUBMIT = "progress:submit"
    PROGRESS_VIEW = "progress:view"
    PHOTO_UPLOAD = "photo:upload"

    # Dashboards / reports
    DASHBOARD_COMPANY = "dashboard:company"
    REPORTS_VIEW = "reports:view"


# Convenience groupings
_MANAGER_TRACKING = {Permission.TRACKING_VIEW_ASSIGNED, Permission.TRACKING_VIEW_SELF}
_FIELD_CONTENT = {
    Permission.TASK_VIEW,
    Permission.ISSUE_VIEW,
    Permission.PROGRESS_VIEW,
    Permission.PHOTO_UPLOAD,
}

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.COMPANY_OWNER: frozenset(Permission),  # all permissions
    Role.HR_ADMIN: frozenset(
        {
            Permission.COMPANY_VIEW,
            Permission.USER_VIEW,
            Permission.USER_CREATE,
            Permission.USER_UPDATE,
            Permission.USER_DEACTIVATE,
            Permission.USER_RESET_PASSWORD,
            Permission.USER_ASSIGN_ROLE,
            Permission.PROJECT_VIEW_ALL,
            Permission.ASSIGNMENT_VIEW,
            Permission.ASSIGNMENT_MANAGE,
            Permission.TRACKING_VIEW_ASSIGNED,
            Permission.REPORTS_VIEW,
        }
    ),
    Role.PROJECT_ENGINEER: frozenset(
        {
            Permission.COMPANY_VIEW,
            Permission.USER_VIEW,
            Permission.PROJECT_VIEW_ASSIGNED,
            Permission.ASSIGNMENT_VIEW,
            Permission.TASK_CREATE,
            Permission.TASK_UPDATE,
            Permission.TASK_APPROVE,
            Permission.ISSUE_CREATE,
            Permission.ISSUE_UPDATE,
            Permission.PROGRESS_VIEW,
            Permission.REPORTS_VIEW,
            *_MANAGER_TRACKING,
            *_FIELD_CONTENT,
        }
    ),
    Role.SITE_ENGINEER: frozenset(
        {
            Permission.COMPANY_VIEW,
            Permission.USER_VIEW,
            Permission.PROJECT_VIEW_ASSIGNED,
            Permission.ASSIGNMENT_VIEW,
            Permission.TASK_CREATE,
            Permission.TASK_UPDATE,
            Permission.ISSUE_CREATE,
            Permission.ISSUE_UPDATE,
            Permission.PROGRESS_SUBMIT,
            *_MANAGER_TRACKING,
            *_FIELD_CONTENT,
        }
    ),
    Role.EMPLOYEE: frozenset(
        {
            Permission.PROJECT_VIEW_ASSIGNED,
            Permission.TRACKING_VIEW_SELF,
            Permission.LOCATION_SHARE,
            Permission.TASK_VIEW,
            Permission.TASK_UPDATE,
            Permission.ISSUE_CREATE,
            Permission.ISSUE_VIEW,
            Permission.PHOTO_UPLOAD,
        }
    ),
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
