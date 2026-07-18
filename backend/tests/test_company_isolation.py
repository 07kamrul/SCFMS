"""Multi-tenant isolation: a user must never see another company's data."""
from __future__ import annotations

import pytest

from app.models.enums import Role
from tests.factories import auth_header, make_company, make_user

pytestmark = pytest.mark.integration


@pytest.fixture
def two_companies(db):
    acme = make_company(db, name="Acme", slug="acme")
    globex = make_company(db, name="Globex", slug="globex")
    make_user(db, company=acme, email="hr@acme.com", role=Role.HR_ADMIN)
    make_user(db, company=acme, email="emp@acme.com", role=Role.EMPLOYEE)
    globex_emp = make_user(db, company=globex, email="emp@globex.com", role=Role.EMPLOYEE)
    return acme, globex, globex_emp


def test_user_list_only_shows_own_company(client, two_companies):
    _, _, _ = two_companies
    headers = auth_header(client, email="hr@acme.com", password="password123")
    resp = client.get("/api/v1/users", headers=headers)
    assert resp.status_code == 200
    emails = {u["email"] for u in resp.json()["data"]}
    assert emails == {"hr@acme.com", "emp@acme.com"}
    assert "emp@globex.com" not in emails


def test_cannot_fetch_user_from_another_company(client, two_companies):
    _, _, globex_emp = two_companies
    headers = auth_header(client, email="hr@acme.com", password="password123")
    resp = client.get(f"/api/v1/users/{globex_emp.id}", headers=headers)
    # Cross-tenant id resolves to not-found, never leaks existence.
    assert resp.status_code == 404


def test_cannot_update_user_from_another_company(client, two_companies):
    _, _, globex_emp = two_companies
    headers = auth_header(client, email="hr@acme.com", password="password123")
    resp = client.patch(
        f"/api/v1/users/{globex_emp.id}",
        headers=headers,
        json={"full_name": "Hacked"},
    )
    assert resp.status_code == 404


def test_identifiers_unique_per_company_not_globally(client, db):
    """Same email can exist in two different companies."""
    acme = make_company(db, name="Acme2", slug="acme2")
    globex = make_company(db, name="Globex2", slug="globex2")
    make_user(db, company=acme, email="shared@x.com", role=Role.COMPANY_OWNER,
              password="password123")
    make_user(db, company=globex, email="shared@x.com", role=Role.COMPANY_OWNER,
              password="different1")
    # Each resolves to its own company via its own password.
    assert auth_header(client, email="shared@x.com", password="password123")
    assert auth_header(client, email="shared@x.com", password="different1")
