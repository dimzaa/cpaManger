"""
Integration tests for Employee API endpoints:
  GET    /api/employees
  GET    /api/employees/{id}
  POST   /api/employees
  PATCH  /api/employees/{id}
  DELETE /api/employees/{id}
"""

import pytest


class TestListEmployees:
    def test_admin_can_list(self, client, auth_headers_admin, employee_user):
        r = client.get("/api/employees", headers=auth_headers_admin)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert any(e["email"] == "emp@test.com" for e in data)

    def test_municipality_user_blocked(self, client, auth_headers_muni):
        r = client.get("/api/employees", headers=auth_headers_muni)
        assert r.status_code in (401, 403)

    def test_employee_user_blocked(self, client, auth_headers_emp):
        r = client.get("/api/employees", headers=auth_headers_emp)
        assert r.status_code in (401, 403)

    def test_unauthenticated_blocked(self, client):
        r = client.get("/api/employees")
        assert r.status_code in (401, 403)

    def test_filter_by_municipality_id(self, client, auth_headers_admin, employee_user, municipality_record):
        r = client.get(
            f"/api/employees?municipality_id={municipality_record.id}",
            headers=auth_headers_admin,
        )
        assert r.status_code == 200

    def test_active_only_filter(self, client, auth_headers_admin, employee_user):
        r = client.get("/api/employees?active_only=true", headers=auth_headers_admin)
        assert r.status_code == 200
        data = r.json()
        assert all(e.get("is_active", True) for e in data)


class TestGetEmployee:
    def test_admin_can_get(self, client, auth_headers_admin, employee_user):
        r = client.get(f"/api/employees/{employee_user.id}", headers=auth_headers_admin)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "emp@test.com"

    def test_nonexistent_returns_404(self, client, auth_headers_admin):
        r = client.get("/api/employees/99999", headers=auth_headers_admin)
        assert r.status_code == 404

    def test_municipality_user_blocked(self, client, auth_headers_muni, employee_user):
        r = client.get(f"/api/employees/{employee_user.id}", headers=auth_headers_muni)
        assert r.status_code in (401, 403)


class TestCreateEmployee:
    def test_admin_can_create_employee(self, client, auth_headers_admin, municipality_record):
        r = client.post("/api/employees", json={
            "email": "newemployee@test.com",
            "password": "EmployeePass1",
            "first_name": "עובד",
            "last_name": "חדש",
            "municipality_ids": [municipality_record.id],
        }, headers=auth_headers_admin)
        assert r.status_code in (200, 201)
        body = r.json()
        # Route returns {"data": {...}, "message": ...}
        employee_data = body.get("data", body)
        assert employee_data["email"] == "newemployee@test.com"

    def test_duplicate_email_returns_400(self, client, auth_headers_admin, employee_user, municipality_record):
        r = client.post("/api/employees", json={
            "email": "emp@test.com",
            "password": "SomePass1",
            "first_name": "Dup",
            "last_name": "User",
            "municipality_ids": [municipality_record.id],
        }, headers=auth_headers_admin)
        assert r.status_code in (400, 409, 422)

    def test_missing_municipality_ids_returns_422(self, client, auth_headers_admin):
        r = client.post("/api/employees", json={
            "email": "noassign@test.com",
            "password": "Pass1234",
            "first_name": "No",
            "last_name": "Assign",
        }, headers=auth_headers_admin)
        assert r.status_code == 422

    def test_municipality_user_cannot_create(self, client, auth_headers_muni, municipality_record):
        r = client.post("/api/employees", json={
            "email": "unauth@test.com",
            "password": "UnAuthPass1",
            "first_name": "Not",
            "last_name": "Allowed",
            "municipality_ids": [municipality_record.id],
        }, headers=auth_headers_muni)
        assert r.status_code in (401, 403)


class TestUpdateEmployee:
    def test_admin_can_update(self, client, auth_headers_admin, employee_user):
        r = client.patch(f"/api/employees/{employee_user.id}", json={
            "first_name": "שם מעודכן",
        }, headers=auth_headers_admin)
        assert r.status_code == 200
        data = r.json()
        assert data["first_name"] == "שם מעודכן"

    def test_update_is_active(self, client, auth_headers_admin, employee_user):
        r = client.patch(f"/api/employees/{employee_user.id}", json={
            "is_active": False,
        }, headers=auth_headers_admin)
        assert r.status_code == 200

    def test_nonexistent_returns_404(self, client, auth_headers_admin):
        r = client.patch("/api/employees/99999", json={"first_name": "x"}, headers=auth_headers_admin)
        assert r.status_code == 404

    def test_municipality_user_cannot_update(self, client, auth_headers_muni, employee_user):
        r = client.patch(f"/api/employees/{employee_user.id}", json={
            "first_name": "hack",
        }, headers=auth_headers_muni)
        assert r.status_code in (401, 403)


class TestDeleteEmployee:
    def test_admin_can_delete(self, client, auth_headers_admin, employee_user):
        r = client.delete(f"/api/employees/{employee_user.id}", headers=auth_headers_admin)
        assert r.status_code in (200, 204)

    def test_delete_nonexistent_returns_404(self, client, auth_headers_admin):
        r = client.delete("/api/employees/99999", headers=auth_headers_admin)
        assert r.status_code == 404

    def test_municipality_user_cannot_delete(self, client, auth_headers_muni, employee_user):
        r = client.delete(f"/api/employees/{employee_user.id}", headers=auth_headers_muni)
        assert r.status_code in (401, 403)
