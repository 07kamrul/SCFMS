"""Authentication flow tests: login, refresh rotation, lockout, password change."""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.models.enums import Role, UserStatus
from tests.factories import auth_header, make_company, make_user

pytestmark = pytest.mark.integration


@pytest.fixture
def company(db):
    return make_company(db, name="Acme Build", slug="acme-build")


@pytest.fixture
def owner(db, company):
    return make_user(db, company=company, email="owner@acme.com", role=Role.COMPANY_OWNER)


def test_login_success_returns_token_pair(client, owner):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@acme.com", "password": "password123"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["user"]["role"] == "company_owner"
    assert body["data"]["tokens"]["access_token"]
    assert body["data"]["tokens"]["refresh_token"]
    # Response must never leak the password hash.
    assert "hashed_password" not in body["data"]["user"]


def test_login_wrong_password_rejected(client, owner):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@acme.com", "password": "wrong-password"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "authentication_failed"


def test_login_locks_after_max_attempts(client, owner):
    for _ in range(settings.MAX_LOGIN_ATTEMPTS):
        client.post(
            "/api/v1/auth/login",
            json={"email": "owner@acme.com", "password": "nope"},
        )
    # Even the correct password is now locked out.
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@acme.com", "password": "password123"},
    )
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "account_locked"


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_returns_current_user(client, owner):
    headers = auth_header(client, email="owner@acme.com", password="password123")
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["email"] == "owner@acme.com"


def test_refresh_rotates_and_old_token_is_revoked(client, owner):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@acme.com", "password": "password123"},
    ).json()
    old_refresh = login["data"]["tokens"]["refresh_token"]

    first = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200
    new_refresh = first.json()["data"]["refresh_token"]
    assert new_refresh != old_refresh

    # Reusing the rotated (old) token is rejected as reuse.
    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401
    assert reuse.json()["error"]["code"] == "token_reuse_detected"


def test_inactive_user_cannot_login(client, db, company):
    make_user(
        db,
        company=company,
        email="ghost@acme.com",
        role=Role.EMPLOYEE,
        status=UserStatus.INACTIVE,
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@acme.com", "password": "password123"},
    )
    assert resp.status_code == 401


def test_login_requires_exactly_one_identifier(client):
    resp = client.post("/api/v1/auth/login", json={"password": "x"})
    assert resp.status_code == 422
