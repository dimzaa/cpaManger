"""
Integration tests for Municipality API endpoints:
  GET  /api/municipalities/
  GET  /api/municipalities/{id}
  POST /api/municipalities/
  PATCH /api/municipalities/{id}
  DELETE /api/municipalities/{id}
"""

import pytest


class TestListMunicipalities:
    def test_list_requires_auth(self, client):
        r = client.get("/api/municipalities/")
        assert r.status_code in (401, 403)

    def test_list_returns_all(self, client, municipality_record, auth_headers_admin):
        r = client.get("/api/municipalities/", headers=auth_headers_admin)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_municipality_user_can_read(self, client, municipality_record, auth_headers_muni):
        r = client.get("/api/municipalities/", headers=auth_headers_muni)
        assert r.status_code == 200

    def test_list_employee_can_read(self, client, municipality_record, auth_headers_emp):
        r = client.get("/api/municipalities/", headers=auth_headers_emp)
        assert r.status_code == 200

    def test_list_item_has_expected_fields(self, client, municipality_record, auth_headers_admin):
        r = client.get("/api/municipalities/", headers=auth_headers_admin)
        items = r.json()
        assert len(items) >= 1
        item = items[0]
        for field in ("id", "name", "code"):
            assert field in item


class TestGetMunicipality:
    def test_get_by_id(self, client, municipality_record, auth_headers_admin):
        r = client.get(f"/api/municipalities/{municipality_record.id}", headers=auth_headers_admin)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == municipality_record.id
        assert data["name"] == municipality_record.name

    def test_get_nonexistent_returns_404(self, client, auth_headers_admin):
        r = client.get("/api/municipalities/99999", headers=auth_headers_admin)
        assert r.status_code == 404

    def test_get_requires_auth(self, client, municipality_record):
        r = client.get(f"/api/municipalities/{municipality_record.id}")
        assert r.status_code in (401, 403)


class TestCreateMunicipality:
    def test_admin_can_create(self, client, auth_headers_admin):
        r = client.post("/api/municipalities/", json={
            "name": "עיריית חדשה",
            "code": "NEW01",
            "login_email": "new@muni.gov.il",
        }, headers=auth_headers_admin)
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["name"] == "עיריית חדשה"
        assert data["code"] == "NEW01"

    def test_municipality_user_cannot_create(self, client, auth_headers_muni):
        r = client.post("/api/municipalities/", json={
            "name": "לא מורשה",
            "code": "NO001",
            "login_email": "no@muni.gov.il",
        }, headers=auth_headers_muni)
        assert r.status_code in (401, 403)

    def test_missing_name_returns_422(self, client, auth_headers_admin):
        r = client.post("/api/municipalities/", json={
            "code": "MISS01",
        }, headers=auth_headers_admin)
        assert r.status_code == 422


class TestUpdateMunicipality:
    def test_admin_can_update(self, client, municipality_record, auth_headers_admin):
        r = client.put(
            f"/api/municipalities/{municipality_record.id}",
            json={"name": "שם מעודכן"},
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "שם מעודכן"

    def test_update_nonexistent_returns_404(self, client, auth_headers_admin):
        r = client.put("/api/municipalities/99999", json={"name": "x"}, headers=auth_headers_admin)
        assert r.status_code == 404

    def test_municipality_user_cannot_update(self, client, municipality_record, auth_headers_muni):
        r = client.put(
            f"/api/municipalities/{municipality_record.id}",
            json={"name": "hack"},
            headers=auth_headers_muni,
        )
        assert r.status_code in (401, 403)


class TestDeleteMunicipality:
    def test_admin_can_delete(self, client, auth_headers_admin, db):
        from backend.models.municipality import Municipality
        muni = Municipality(name="למחיקה", code="DEL01", login_email="del@test.com")
        db.add(muni)
        db.commit()
        db.refresh(muni)
        r = client.delete(f"/api/municipalities/{muni.id}", headers=auth_headers_admin)
        assert r.status_code in (200, 204)

    def test_delete_nonexistent_returns_404(self, client, auth_headers_admin):
        r = client.delete("/api/municipalities/99999", headers=auth_headers_admin)
        assert r.status_code == 404

    def test_municipality_user_cannot_delete(self, client, municipality_record, auth_headers_muni):
        r = client.delete(f"/api/municipalities/{municipality_record.id}", headers=auth_headers_muni)
        assert r.status_code in (401, 403)
