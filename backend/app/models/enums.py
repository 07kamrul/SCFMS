"""Shared enumerations used across models and schemas.

Kept in one place so the mobile app, API schemas, and DB stay in lock-step.
Roles are fixed (5 total) — RBAC is a static code-defined matrix rather than
runtime-editable tables (YAGNI: the product spec defines no role customization).
"""
from __future__ import annotations

import enum


class Role(str, enum.Enum):
    COMPANY_OWNER = "company_owner"
    HR_ADMIN = "hr_admin"
    PROJECT_ENGINEER = "project_engineer"
    SITE_ENGINEER = "site_engineer"
    EMPLOYEE = "employee"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class ProjectStatus(str, enum.Enum):
    PLANNED = "planned"
    RUNNING = "running"
    ON_HOLD = "on_hold"
    DELAYED = "delayed"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class AssignmentRole(str, enum.Enum):
    PROJECT_ENGINEER = "project_engineer"
    SITE_ENGINEER = "site_engineer"
    EMPLOYEE = "employee"


class LocationStatus(str, enum.Enum):
    INSIDE_ASSIGNED = "inside_assigned"
    NEAR_ASSIGNED = "near_assigned"
    OUTSIDE_ASSIGNED = "outside_assigned"
    INSIDE_OTHER_ACCESSIBLE = "inside_other_accessible"
    INSIDE_OTHER_UNAUTHORIZED = "inside_other_unauthorized"
    NO_ASSIGNED_PROJECT = "no_assigned_project"
    LOCATION_DISABLED = "location_disabled"
    OFFLINE = "offline"
    OUTSIDE_TRACKING_HOURS = "outside_tracking_hours"
    UNKNOWN = "unknown"


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class IssueStatus(str, enum.Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"


class IssuePriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueCategory(str, enum.Enum):
    WORK_DELAY = "work_delay"
    DESIGN_PROBLEM = "design_problem"
    WORKER_SHORTAGE = "worker_shortage"
    SITE_ACCESS_PROBLEM = "site_access_problem"
    CLIENT_CHANGE = "client_change"
    WEATHER = "weather"
    QUALITY_PROBLEM = "quality_problem"
    UTILITY_PROBLEM = "utility_problem"
    APPROVAL_PROBLEM = "approval_problem"
    OTHER = "other"
