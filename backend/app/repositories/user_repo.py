"""User data access, always tenant-scoped."""
from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select

from app.models.enums import Role
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_identifier(
        self, *, company_id: uuid.UUID, email: str | None, phone: str | None
    ) -> User | None:
        conditions = []
        if email:
            conditions.append(func.lower(User.email) == email.lower())
        if phone:
            conditions.append(User.phone == phone)
        if not conditions:
            return None
        stmt = select(User).where(User.company_id == company_id, or_(*conditions))
        return self.db.execute(stmt).scalar_one_or_none()

    def find_login_candidates(
        self, *, email: str | None, phone: str | None
    ) -> list[User]:
        """Find users across all companies matching the identifier.

        Login has no company context yet, so we resolve the tenant from the
        matched user. Identifiers are unique per company, so cross-company
        collisions are possible but rare; we return all and the service picks.
        """
        conditions = []
        if email:
            conditions.append(func.lower(User.email) == email.lower())
        if phone:
            conditions.append(User.phone == phone)
        if not conditions:
            return []
        stmt = select(User).where(or_(*conditions))
        return list(self.db.execute(stmt).scalars().all())

    def list_for_company(
        self,
        *,
        company_id: uuid.UUID,
        role: Role | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        base = select(User).where(User.company_id == company_id)
        if role:
            base = base.where(User.role == role)
        if search:
            like = f"%{search.lower()}%"
            base = base.where(
                or_(
                    func.lower(User.full_name).like(like),
                    func.lower(User.email).like(like),
                    User.phone.like(f"%{search}%"),
                )
            )
        total = int(
            self.db.execute(
                select(func.count()).select_from(base.subquery())
            ).scalar_one()
        )
        rows = list(
            self.db.execute(
                base.order_by(User.full_name).offset(offset).limit(limit)
            ).scalars().all()
        )
        return rows, total
