"""Shared FastAPI dependencies: DB session, current user, permission guards.

`get_current_user` decodes the JWT, then re-loads the user from the DB to
confirm they still exist, are active, and belong to the company in the token.
This is where multi-tenant isolation is anchored: downstream code trusts
`current_user.company_id`.
"""
from __future__ import annotations

from collections.abc import Callable

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import Role, UserStatus
from app.models.user import User
from app.permissions.roles import Permission, has_permission
from app.repositories.user_repo import UserRepository

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Missing authentication token.")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Access token expired.", error_code="token_expired")
    except jwt.PyJWTError:
        raise AuthenticationError("Invalid access token.")

    user = UserRepository(db).get(payload["sub"])
    if user is None:
        raise AuthenticationError("User no longer exists.")
    if str(user.company_id) != payload.get("company_id"):
        raise AuthenticationError("Token/company mismatch.")
    if user.status != UserStatus.ACTIVE:
        raise AuthenticationError("Account is not active.")

    # Stash on request state for downstream logging/audit.
    request.state.user = user
    return user


def require_permission(permission: Permission) -> Callable[[User], User]:
    """Dependency factory enforcing a single permission from the RBAC matrix."""

    def _guard(current_user: User = Depends(get_current_user)) -> User:
        if not has_permission(current_user.role, permission):
            raise PermissionDeniedError(
                f"Your role ({current_user.role.value}) lacks permission "
                f"'{permission.value}'."
            )
        return current_user

    return _guard


def require_roles(*roles: Role) -> Callable[[User], User]:
    """Dependency factory restricting an endpoint to specific roles."""
    allowed = set(roles)

    def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise PermissionDeniedError("Your role cannot access this resource.")
        return current_user

    return _guard


def require_any_permission(*permissions: Permission) -> Callable[[User], User]:
    """Dependency factory allowing access if the role has ANY of the given
    permissions (e.g. project:view_all OR project:view_assigned)."""

    def _guard(current_user: User = Depends(get_current_user)) -> User:
        if not any(has_permission(current_user.role, p) for p in permissions):
            names = ", ".join(p.value for p in permissions)
            raise PermissionDeniedError(
                f"Your role ({current_user.role.value}) lacks all of: {names}."
            )
        return current_user

    return _guard
