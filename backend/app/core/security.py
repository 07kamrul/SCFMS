"""Password hashing (Argon2) and JWT access-token handling.

Refresh tokens are opaque random strings persisted (hashed) in the DB so
they can be revoked and rotated; only the access token is a JWT.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings

_ph = PasswordHasher()

ACCESS_TOKEN_TYPE = "access"


# ── Passwords ─────────────────────────────────────────────────────────────
def hash_password(plain_password: str) -> str:
    return _ph.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError, Exception):
        return False


def needs_rehash(hashed_password: str) -> bool:
    try:
        return _ph.check_needs_rehash(hashed_password)
    except Exception:
        return False


# ── Access token (JWT) ──────────────────────────────────────────────────────
def create_access_token(
    *,
    user_id: uuid.UUID,
    company_id: uuid.UUID,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "company_id": str(company_id),
        "role": role,
        "type": ACCESS_TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode & validate a JWT access token. Raises jwt exceptions on failure."""
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp", "sub", "type"]},
    )
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise jwt.InvalidTokenError("Wrong token type")
    return payload


# ── Refresh tokens (opaque, DB-backed) ───────────────────────────────────────
def generate_refresh_token() -> str:
    """A high-entropy opaque token handed to the client."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw_token: str) -> str:
    """Store only the SHA-256 of the refresh token so a DB leak can't replay it."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
