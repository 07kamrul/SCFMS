"""Authentication request/response schemas.

Note: response models deliberately never expose password hashes or the
refresh-token hash — only the opaque tokens the client needs.
"""
from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.enums import Role, UserStatus


class LoginRequest(BaseModel):
    # Login by email OR phone; exactly one identifier required.
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    password: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def _require_one_identifier(self) -> "LoginRequest":
        if not self.email and not self.phone:
            raise ValueError("Provide either email or phone.")
        if self.email and self.phone:
            raise ValueError("Provide only one of email or phone, not both.")
        return self


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=512)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=512)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)

    @model_validator(mode="after")
    def _require_one_identifier(self) -> "ForgotPasswordRequest":
        if not self.email and not self.phone:
            raise ValueError("Provide either email or phone.")
        return self


class ResetPasswordRequest(BaseModel):
    reset_token: str = Field(min_length=10, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserPublic(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    full_name: str
    email: EmailStr | None
    phone: str | None
    role: Role
    status: UserStatus
    profile_photo_url: str | None
    job_title: str | None
    is_identity_verified: bool

    model_config = {"from_attributes": True}


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # access-token lifetime in seconds


class LoginResponse(BaseModel):
    user: UserPublic
    tokens: TokenPair
