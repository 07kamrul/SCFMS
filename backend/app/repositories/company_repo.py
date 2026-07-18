"""Company and company-settings data access."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.company import Company, CompanySettings
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    model = Company

    def get_by_slug(self, slug: str) -> Company | None:
        return self.db.execute(
            select(Company).where(Company.slug == slug)
        ).scalar_one_or_none()

    def get_settings(self, company_id: uuid.UUID) -> CompanySettings | None:
        return self.db.execute(
            select(CompanySettings).where(CompanySettings.company_id == company_id)
        ).scalar_one_or_none()
