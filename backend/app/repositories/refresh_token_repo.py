"""Refresh-token data access for rotation and revocation."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).scalar_one_or_none()

    def revoke(self, token: RefreshToken, *, replaced_by: uuid.UUID | None = None) -> None:
        token.revoked = True
        token.revoked_at = datetime.now(timezone.utc)
        token.replaced_by = replaced_by
        self.db.flush()

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
            .values(revoked=True, revoked_at=datetime.now(timezone.utc))
        )
        self.db.flush()
