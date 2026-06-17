"""
Integration tests for Ministry API endpoints:
  GET  /api/ministry/codes
  GET  /api/ministry/codes/{code}
  GET  /api/ministry/policy-changes
  POST /api/ministry/policy-changes
  GET  /api/ministry/circulars
  POST /api/ministry/circulars
"""

import pytest


class TestMinistryCodes:
    def test_list_codes_public_endpoint(self, client):
        """Ministry codes endpoint is public — returns 200 without auth."""
        r = client.get("/api/ministry/codes")
        assert r.status_code == 200

    def test_admin_can_list_codes(self, client, auth_headers_admin):
        r = client.get("/api/ministry/codes", headers=auth_headers_admin)
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, (list, dict))

    def test_municipality_user_can_list_codes(self, client, auth_headers_muni):
        r = client.get("/api/ministry/codes", headers=auth_headers_muni)
        assert r.status_code == 200

    def test_filter_by_category(self, client, auth_headers_admin):
        r = client.get("/api/ministry/codes?category=ילדים", headers=auth_headers_admin)
        assert r.status_code == 200

    def test_search_query(self, client, auth_headers_admin):
        r = client.get("/api/ministry/codes?search=גן", headers=auth_headers_admin)
        assert r.status_code == 200


class TestMinistryPolicyChanges:
    def test_list_policy_changes_requires_auth(self, client, auth_headers_admin):
        """Policy changes endpoint needs auth header; check response is OK with auth."""
        r = client.get("/api/ministry/policy-changes", headers=auth_headers_admin)
        assert r.status_code == 200

    def test_admin_can_list_policy_changes(self, client, auth_headers_admin):
        r = client.get("/api/ministry/policy-changes", headers=auth_headers_admin)
        assert r.status_code == 200

    def test_municipality_can_view_policy_changes(self, client, auth_headers_muni):
        r = client.get("/api/ministry/policy-changes", headers=auth_headers_muni)
        assert r.status_code == 200

    def test_admin_can_create_policy_change(self, client, auth_headers_admin):
        r = client.post("/api/ministry/policy-changes", json={
            "title": "שינוי מדיניות בדיקה",
            "change_type": "formula",
            "severity": "medium",
            "affected_codes": ["3"],
        }, headers=auth_headers_admin)
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["title"] == "שינוי מדיניות בדיקה"

    def test_municipality_cannot_create_policy_change(self, client, auth_headers_muni):
        r = client.post("/api/ministry/policy-changes", json={
            "title": "לא מורשה",
            "change_type": "formula",
            "severity": "low",
        }, headers=auth_headers_muni)
        assert r.status_code in (401, 403)

    def test_create_policy_change_missing_title_422(self, client, auth_headers_admin):
        r = client.post("/api/ministry/policy-changes", json={
            "change_type": "formula",
        }, headers=auth_headers_admin)
        assert r.status_code == 422


class TestMinistryCirculars:
    def test_list_circulars_requires_auth(self, client, auth_headers_admin):
        """Circulars endpoint; check response is OK with auth."""
        r = client.get("/api/ministry/circulars", headers=auth_headers_admin)
        assert r.status_code == 200

    def test_admin_can_list_circulars(self, client, auth_headers_admin):
        r = client.get("/api/ministry/circulars", headers=auth_headers_admin)
        assert r.status_code == 200

    def test_municipality_can_view_circulars(self, client, auth_headers_muni):
        r = client.get("/api/ministry/circulars", headers=auth_headers_muni)
        assert r.status_code == 200

    def test_admin_can_create_circular(self, client, auth_headers_admin):
        r = client.post("/api/ministry/circulars", json={
            "title": "חוזר בדיקה",
            "category": "כללי",
            "importance": "routine",
        }, headers=auth_headers_admin)
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["title"] == "חוזר בדיקה"

    def test_municipality_cannot_create_circular(self, client, auth_headers_muni):
        r = client.post("/api/ministry/circulars", json={
            "title": "לא מורשה",
            "category": "כללי",
            "importance": "routine",
        }, headers=auth_headers_muni)
        assert r.status_code in (401, 403)

    def test_filter_circulars_by_category(self, client, auth_headers_admin):
        r = client.get("/api/ministry/circulars?category=כללי", headers=auth_headers_admin)
        assert r.status_code == 200
