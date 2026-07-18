"""Employee/user management by HR Admin and Company Owner."""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.enums import Role, UserStatus
from app.models.user import User
from app.repositories.refresh_token_repo import RefreshTokenRepository
from app.repositories.user_repo import UserRepository
from app.schemas.common import PaginationParams
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.tokens = RefreshTokenRepository(db)

    def create(self, *, company_id: uuid.UUID, payload: UserCreate) -> User:
        existing = self.users.get_by_identifier(
            company_id=company_id, email=payload.email, phone=payload.phone
        )
        if existing is not None:
            raise ConflictError("A user with this email or phone already exists.")

        user = User(
            company_id=company_id,
            full_name=payload.full_name,
            email=payload.email,
            phone=payload.phone,
            hashed_password=hash_password(payload.password),
            role=payload.role,
            job_title=payload.job_title,
            status=UserStatus.ACTIVE,
        )
        self.users.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get(self, *, company_id: uuid.UUID, user_id: uuid.UUID) -> User:
        user = self.users.get_for_company(user_id, company_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user

    def list(
        self,
        *,
        company_id: uuid.UUID,
        role: Role | None,
        search: str | None,
        pagination: PaginationParams,
    ) -> tuple[list[User], int]:
        return self.users.list_for_company(
            company_id=company_id,
            role=role,
            search=search,
            offset=pagination.offset,
            limit=pagination.page_size,
        )

    def update(
        self, *, company_id: uuid.UUID, user_id: uuid.UUID, payload: UserUpdate
    ) -> User:
        user = self.get(company_id=company_id, user_id=user_id)
        data = payload.model_dump(exclude_unset=True)

        # Uniqueness re-check if contact details change.
        new_email = data.get("email", user.email)
        new_phone = data.get("phone", user.phone)
        if ("email" in data or "phone" in data):
            clash = self.users.get_by_identifier(
                company_id=company_id, email=new_email, phone=new_phone
            )
            if clash is not None and clash.id != user.id:
                raise ConflictError("Another user already uses this email or phone.")

        for key, value in data.items():
            setattr(user, key, value)

        # Deactivating a user revokes their sessions.
        if data.get("status") in {UserStatus.INACTIVE, UserStatus.SUSPENDED}:
            self.tokens.revoke_all_for_user(user.id)

        self.db.commit()
        self.db.refresh(user)
        return user

    def reset_password(
        self, *, company_id: uuid.UUID, user_id: uuid.UUID, new_password: str
    ) -> None:
        user = self.get(company_id=company_id, user_id=user_id)
        user.hashed_password = hash_password(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        self.tokens.revoke_all_for_user(user.id)
        self.db.commit()

    def set_status(
        self, *, company_id: uuid.UUID, user_id: uuid.UUID, status: UserStatus
    ) -> User:
        return self.update(
            company_id=company_id,
            user_id=user_id,
            payload=UserUpdate(status=status),
        )
