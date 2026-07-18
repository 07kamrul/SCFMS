"""Role-based access control: the permission matrix is enforced at the API."""
from __future__ import annotations

import pytest

from app.models.enums import Role
from app.permissions.roles import Permission, has_permission
from tests.factories import auth_header, make_company, make_user

pytestmark = pytest.mark.integration


@pytest.fixture
def company(db):
    c = make_company(db, name="Buildco", slug="buildco")
    make_user(db, company=c, email="owner@buildco.com", role=Role.COMPANY_OWNER)
    make_user(db, company=c, email="hr@buildco.com", role=Role.HR_ADMIN)
    make_user(db, company=c, email="emp@buildco.com", role=Role.EMPLOYEE)
    return c


def test_matrix_owner_has_everything():
    for perm in Permission:
        assert has_permission(Role.COMPANY_OWNER, perm)


def test_matrix_employee_cannot_create_users():
    assert not has_permission(Role.EMPLOYEE, Permission.USER_CREATE)
    assert has_permission(Role.EMPLOYEE, Permission.LOCATION_SHARE)


def test_employee_cannot_create_user_via_api(client, company):
    headers = auth_header(client, email="emp@buildco.com", password="password123")
    resp = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "full_name": "New Guy",
            "email": "new@buildco.com",
            "password": "password123",
            "role": "employee",
        },
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "permission_denied"


def test_hr_can_create_user_via_api(client, company):
    headers = auth_header(client, email="hr@buildco.com", password="password123")
    resp = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "full_name": "New Worker",
            "email": "worker@buildco.com",
            "password": "password123",
            "role": "employee",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["data"]["email"] == "worker@buildco.com"


def test_only_owner_can_manage_company_settings(client, company):
    hr = auth_header(client, email="hr@buildco.com", password="password123")
    owner = auth_header(client, email="owner@buildco.com", password="password123")

    assert client.patch(
        "/api/v1/companies/settings", headers=hr, json={"near_distance_meters": 500}
    ).status_code == 403
    assert client.patch(
        "/api/v1/companies/settings", headers=owner, json={"near_distance_meters": 500}
    ).status_code == 200
