"""Company registration and settings management."""
from __future__ import annotations

import re
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.company import Company, CompanySettings
from app.models.enums import Role
from app.models.user import User
from app.repositories.company_repo import CompanyRepository
from app.repositories.user_repo import UserRepository
from app.schemas.company import CompanyRegister, CompanySettingsUpdate


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "company"


class CompanyService:
    def __init__(self, db: Session):
        self.db = db
        self.companies = CompanyRepository(db)
        self.users = UserRepository(db)

    def register(self, payload: CompanyRegister) -> tuple[Company, User]:
        """Create a company and its first Company Owner user atomically."""
        base_slug = _slugify(payload.company_name)
        slug = self._unique_slug(base_slug)

        company = Company(name=payload.company_name, slug=slug, is_active=True)
        self.companies.add(company)

        settings_row = CompanySettings(company_id=company.id)
        self.db.add(settings_row)

        owner = User(
            company_id=company.id,
            full_name=payload.owner_full_name,
            email=payload.owner_email,
            phone=payload.owner_phone,
            hashed_password=hash_password(payload.owner_password),
            role=Role.COMPANY_OWNER,
        )
        self.users.add(owner)
        self.db.commit()
        self.db.refresh(company)
        self.db.refresh(owner)
        return company, owner

    def _unique_slug(self, base: str) -> str:
        slug = base
        suffix = 1
        while self.companies.get_by_slug(slug) is not None:
            suffix += 1
            slug = f"{base}-{suffix}"
        return slug

    def get_settings(self, company_id: uuid.UUID) -> CompanySettings:
        row = self.companies.get_settings(company_id)
        if row is None:
            raise NotFoundError("Company settings not found.")
        return row

    def update_settings(
        self, company_id: uuid.UUID, payload: CompanySettingsUpdate
    ) -> CompanySettings:
        row = self.get_settings(company_id)
        data = payload.model_dump(exclude_unset=True)
        if (
            data.get("tracking_start_hour") is not None
            and data.get("tracking_end_hour") is not None
            and data["tracking_start_hour"] >= data["tracking_end_hour"]
        ):
            raise ConflictError("tracking_start_hour must be before tracking_end_hour.")
        for key, value in data.items():
            setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return row
