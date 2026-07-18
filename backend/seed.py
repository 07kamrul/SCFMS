"""Seed a demo company with one user per role for local development.

Idempotent: re-running updates passwords but does not duplicate rows.
Run:  python seed.py   (with a migrated database and .env in place)
"""
from __future__ import annotations

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.company import Company, CompanySettings
from app.models.enums import Role, UserStatus
from app.models.user import User

DEMO_SLUG = "demo-construction"

DEMO_USERS = [
    ("Olivia Owner", "owner@demo.com", "+8801711000001", Role.COMPANY_OWNER, "owner123"),
    ("Hina HR", "hr@demo.com", "+8801711000002", Role.HR_ADMIN, "hr123456"),
    ("Peter PE", "pe@demo.com", "+8801711000003", Role.PROJECT_ENGINEER, "pe123456"),
    ("Sara SE", "se@demo.com", "+8801711000004", Role.SITE_ENGINEER, "se123456"),
    ("Emil Employee", "emp@demo.com", "+8801711000005", Role.EMPLOYEE, "emp12345"),
]


def seed() -> None:
    db = SessionLocal()
    try:
        company = (
            db.query(Company).filter(Company.slug == DEMO_SLUG).one_or_none()
        )
        if company is None:
            company = Company(name="Demo Construction Co.", slug=DEMO_SLUG, is_active=True)
            db.add(company)
            db.flush()
            db.add(CompanySettings(company_id=company.id))
            print(f"Created company {company.name} ({company.id})")

        for full_name, email, phone, role, password in DEMO_USERS:
            user = (
                db.query(User)
                .filter(User.company_id == company.id, User.email == email)
                .one_or_none()
            )
            if user is None:
                user = User(
                    company_id=company.id,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    hashed_password=hash_password(password),
                    role=role,
                    status=UserStatus.ACTIVE,
                    is_identity_verified=True,
                )
                db.add(user)
                print(f"  + {role.value:18} {email}  (password: {password})")
            else:
                user.hashed_password = hash_password(password)
                print(f"  ~ {role.value:18} {email}  (password reset)")

        db.commit()
        print("\nSeed complete. Log in with any credential above.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
