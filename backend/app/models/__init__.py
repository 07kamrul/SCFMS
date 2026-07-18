"""Model registry.

Importing every model here ensures they are all registered on `Base.metadata`
before Alembic autogenerate or `create_all` runs.
"""
from app.db.base import Base
from app.models.activity_log import ActivityLog
from app.models.company import Company, CompanySettings
from app.models.refresh_token import RefreshToken
from app.models.user import User

__all__ = [
    "Base",
    "ActivityLog",
    "Company",
    "CompanySettings",
    "RefreshToken",
    "User",
]
