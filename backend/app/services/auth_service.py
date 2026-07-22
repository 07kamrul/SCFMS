"""Authentication business logic: login, refresh rotation, logout, password change.

All token issuance, revocation, and login-lockout policy lives here so route
handlers stay thin. Commits happen at this layer's public methods.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationError, RateLimitError, ValidationError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    needs_rehash,
    refresh_token_expiry,
    verify_password,
)
from app.models.enums import UserStatus
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repo import RefreshTokenRepository
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginResponse, TokenPair, UserPublic


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.tokens = RefreshTokenRepository(db)

    # ── Login ────────────────────────────────────────────────────────────
    def login(
        self,
        *,
        email: str | None,
        phone: str | None,
        password: str,
    ) -> LoginResponse:
        candidates = self.users.find_login_candidates(email=email, phone=phone)
        # Pick the first candidate whose password matches (identifiers are
        # unique per company; cross-company collision is rare).
        user = self._select_authenticated_user(candidates, password)
        if user is None:
            # Consume an attempt on any matched-but-wrong-password candidate.
            for c in candidates:
                self._register_failed_attempt(c)
            self.db.commit()
            raise AuthenticationError("Invalid credentials.")

        self._guard_account_state(user)

        # Successful login: reset counters, opportunistically rehash password.
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        if needs_rehash(user.hashed_password):
            user.hashed_password = hash_password(password)

        tokens = self._issue_token_pair(user)
        self.db.commit()
        return LoginResponse(user=UserPublic.model_validate(user), tokens=tokens)

    def _select_authenticated_user(
        self, candidates: list[User], password: str
    ) -> User | None:
        for user in candidates:
            if verify_password(password, user.hashed_password):
                return user
        return None

    def _guard_account_state(self, user: User) -> None:
        now = datetime.now(timezone.utc)
        if user.locked_until and user.locked_until > now:
            raise RateLimitError(
                "Account temporarily locked due to failed login attempts.",
                error_code="account_locked",
            )
        if user.status != UserStatus.ACTIVE:
            raise AuthenticationError("This account is not active.")
        if not user.company.is_active:
            raise AuthenticationError("This company account is disabled.")

    def _register_failed_attempt(self, user: User) -> None:
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            from datetime import timedelta

            user.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.LOGIN_LOCKOUT_MINUTES
            )
            user.failed_login_attempts = 0

    # ── Refresh (rotation with reuse detection) ────────────────────────────
    def refresh(self, *, raw_refresh_token: str) -> TokenPair:
        token_hash = hash_refresh_token(raw_refresh_token)
        stored = self.tokens.get_by_hash(token_hash)
        if stored is None:
            raise AuthenticationError("Invalid refresh token.")

        now = datetime.now(timezone.utc)
        if stored.revoked:
            # Reuse of a rotated token → likely theft. Revoke the whole family.
            self.tokens.revoke_all_for_user(stored.user_id)
            self.db.commit()
            raise AuthenticationError(
                "Refresh token has been revoked.", error_code="token_reuse_detected"
            )
        if stored.expires_at <= now:
            raise AuthenticationError("Refresh token expired.")

        user = self.users.get(stored.user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            raise AuthenticationError("Account is no longer active.")

        new_pair = self._issue_token_pair(user)
        # Rotate: revoke the old token, link to the replacement.
        latest = user.refresh_tokens[-1] if user.refresh_tokens else None
        self.tokens.revoke(stored, replaced_by=latest.id if latest else None)
        self.db.commit()
        return new_pair

    # ── Logout ──────────────────────────────────────────────────────────
    def logout(self, *, raw_refresh_token: str) -> None:
        stored = self.tokens.get_by_hash(hash_refresh_token(raw_refresh_token))
        if stored and not stored.revoked:
            self.tokens.revoke(stored)
            self.db.commit()

    def logout_all(self, *, user_id: uuid.UUID) -> None:
        self.tokens.revoke_all_for_user(user_id)
        self.db.commit()

    # ── Change password ──────────────────────────────────────────────────
    def change_password(
        self, *, user: User, current_password: str, new_password: str
    ) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise ValidationError("Current password is incorrect.")
        user.hashed_password = hash_password(new_password)
        # Force re-login on all other devices for safety.
        self.tokens.revoke_all_for_user(user.id)
        self.db.commit()

    # ── Helpers ─────────────────────────────────────────────────────────
    def _issue_token_pair(self, user: User) -> TokenPair:
        access = create_access_token(
            user_id=user.id, company_id=user.company_id, role=user.role.value
        )
        raw_refresh = generate_refresh_token()
        record = RefreshToken(
            user_id=user.id,
            company_id=user.company_id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=refresh_token_expiry(),
        )
        self.tokens.add(record)
        # Keep the relationship in sync so rotation can find the latest token.
        user.refresh_tokens.append(record)
        return TokenPair(
            access_token=access,
            refresh_token=raw_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
