"""Small helpers to build companies and users in tests."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.company import Company, CompanySettings
from app.models.enums import Role, UserStatus
from app.models.user import User


def make_company(db: Session, *, name: str, slug: str) -> Company:
    company = Company(name=name, slug=slug, is_active=True)
    db.add(company)
    db.flush()
    db.add(CompanySettings(company_id=company.id))
    db.flush()
    return company


def make_user(
    db: Session,
    *,
    company: Company,
    email: str,
    role: Role,
    password: str = "password123",
    phone: str | None = None,
    status: UserStatus = UserStatus.ACTIVE,
) -> User:
    user = User(
        company_id=company.id,
        full_name=email.split("@")[0].title(),
        email=email,
        phone=phone,
        hashed_password=hash_password(password),
        role=role,
        status=status,
    )
    db.add(user)
    db.flush()
    return user


def auth_header(client, *, email: str, password: str) -> dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["data"]["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
