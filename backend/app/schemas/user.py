"""User management schemas (create/update by HR Admin / Owner)."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.enums import Role, UserStatus
from app.schemas.auth import UserPublic

__all__ = ["UserPublic", "UserCreate", "UserUpdate", "PasswordResetByAdmin"]


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    role: Role
    job_title: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def _require_contact(self) -> "UserCreate":
        if not self.email and not self.phone:
            raise ValueError("Provide at least one of email or phone.")
        return self


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    role: Role | None = None
    status: UserStatus | None = None
    job_title: str | None = Field(default=None, max_length=120)
    is_identity_verified: bool | None = None
    profile_photo_url: str | None = Field(default=None, max_length=500)


class PasswordResetByAdmin(BaseModel):
    user_id: uuid.UUID
    new_password: str = Field(min_length=8, max_length=128)
