"""
Integration tests for the Auth API endpoints:
  POST /api/auth/register
  POST /api/auth/login
  GET  /api/auth/me
"""

import pytest
from tests.conftest import make_token


class TestRegister:
    def test_register_admin_without_municipality(self, client):
        r = client.post("/api/auth/register", json={
            "email": "newadmin@test.com",
            "password": "SecurePass1",
            "first_name": "New",
            "last_name": "Admin",
        })
        assert r.status_code in (200, 201)
        assert r.json()["role"] == "admin"

    def test_register_with_municipality_id_gets_municipality_role(
        self, client, municipality_record
    ):
        r = client.post("/api/auth/register", json={
            "email": "muniuser@test.com",
            "password": "SecurePass1",
            "first_name": "Muni",
            "last_name": "User",
            "municipality_id": municipality_record.id,
        })
        assert r.status_code in (200, 201)
        assert r.json()["role"] == "municipality"

    def test_register_duplicate_email_returns_400(self, client, admin_user):
        r = client.post("/api/auth/register", json={
            "email": admin_user.email,
            "password": "AnotherPass1",
            "first_name": "A",
            "last_name": "B",
        })
        assert r.status_code == 400

    def test_register_short_password_returns_422(self, client):
        r = client.post("/api/auth/register", json={
            "email": "short@test.com",
            "password": "abc",
            "first_name": "S",
            "last_name": "P",
        })
        assert r.status_code == 422

    def test_register_missing_email_returns_422(self, client):
        r = client.post("/api/auth/register", json={
            "password": "SecurePass1",
            "first_name": "A",
            "last_name": "B",
        })
        assert r.status_code == 422

    def test_register_invalid_email_returns_422(self, client):
        r = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "SecurePass1",
            "first_name": "A",
            "last_name": "B",
        })
        assert r.status_code == 422

    def test_register_response_has_expected_fields(self, client):
        r = client.post("/api/auth/register", json={
            "email": "fieldcheck@test.com",
            "password": "SecurePass1",
            "first_name": "F",
            "last_name": "C",
        })
        assert r.status_code in (200, 201)
        data = r.json()
        for field in ("id", "email", "role"):
            assert field in data


class TestLogin:
    def test_login_valid_credentials_returns_token(self, client, admin_user):
        r = client.post("/api/auth/login", json={
            "email": "admin@test.com",
            "password": "AdminPass1",
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_returns_user_object(self, client, admin_user):
        r = client.post("/api/auth/login", json={
            "email": "admin@test.com",
            "password": "AdminPass1",
        })
        assert r.status_code == 200
        user = r.json().get("user")
        assert user is not None
        assert user["email"] == "admin@test.com"
        assert user["role"] == "admin"

    def test_login_wrong_password_returns_401(self, client, admin_user):
        r = client.post("/api/auth/login", json={
            "email": "admin@test.com",
            "password": "WrongPassword",
        })
        assert r.status_code in (400, 401)

    def test_login_unknown_email_returns_401(self, client):
        r = client.post("/api/auth/login", json={
            "email": "nobody@test.com",
            "password": "SomePass1",
        })
        assert r.status_code in (400, 401)

    def test_login_inactive_user_blocked(self, client, db, admin_user):
        admin_user.is_active = False
        db.commit()
        r = client.post("/api/auth/login", json={
            "email": "admin@test.com",
            "password": "AdminPass1",
        })
        assert r.status_code in (400, 401, 403)

    def test_login_missing_fields_returns_422(self, client):
        r = client.post("/api/auth/login", json={"email": "admin@test.com"})
        assert r.status_code == 422


class TestGetMe:
    def test_me_returns_current_user(self, client, admin_user, auth_headers_admin):
        r = client.get("/api/auth/me", headers=auth_headers_admin)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "admin@test.com"
        assert data["role"] == "admin"

    def test_me_requires_auth(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code in (401, 403)

    def test_me_invalid_token_returns_401(self, client):
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer not.valid.token"})
        assert r.status_code == 401

    def test_me_municipality_user(self, client, municipality_user, auth_headers_muni):
        r = client.get("/api/auth/me", headers=auth_headers_muni)
        assert r.status_code == 200
        data = r.json()
        assert data["role"] == "municipality"
