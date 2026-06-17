"""
Integration tests for Preset Explanations API endpoints:
  GET    /api/presets
  GET    /api/presets/{id}
  POST   /api/presets
  PATCH  /api/presets/{id}
  DELETE /api/presets/{id}
"""

import pytest


def seed_preset(db, admin_user, **kwargs):
    """Helper: create and persist a PresetExplanation record."""
    from backend.models.preset_explanation import PresetExplanation
    defaults = dict(
        topic_code="3",
        preset_text="הסבר ברירת מחדל לבדיקה",
        category="increase",
        is_active=True,
        created_by=admin_user.id,
    )
    defaults.update(kwargs)
    p = PresetExplanation(**defaults)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


class TestGetPresets:
    def test_anyone_can_list(self, client, db, admin_user):
        seed_preset(db, admin_user)
        r = client.get("/api/presets")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_filter_by_topic_code(self, client, db, admin_user):
        seed_preset(db, admin_user, topic_code="19")
        r = client.get("/api/presets?topic_code=19")
        assert r.status_code == 200
        data = r.json()
        assert all(p["topic_code"] == "19" for p in data)

    def test_active_only_true_excludes_inactive(self, client, db, admin_user):
        seed_preset(db, admin_user, is_active=False, preset_text="לא פעיל")
        r = client.get("/api/presets?active_only=true")
        assert r.status_code == 200
        data = r.json()
        assert all(p["is_active"] for p in data)

    def test_active_only_false_includes_inactive(self, client, db, admin_user):
        seed_preset(db, admin_user, is_active=False, preset_text="לא פעיל")
        r = client.get("/api/presets?active_only=false")
        assert r.status_code == 200
        data = r.json()
        assert any(not p["is_active"] for p in data)


class TestCreatePreset:
    def test_admin_can_create(self, client, auth_headers_admin):
        r = client.post("/api/presets", json={
            "topic_code": "3",
            "preset_text": "טקסט הסבר חדש",
            "category": "increase",
        }, headers=auth_headers_admin)
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["preset_text"] == "טקסט הסבר חדש"
        assert data["topic_code"] == "3"
        assert data["is_active"] is True

    def test_employee_cannot_create(self, client, auth_headers_emp):
        r = client.post("/api/presets", json={
            "topic_code": "3",
            "preset_text": "לא מורשה",
            "category": "other",
        }, headers=auth_headers_emp)
        assert r.status_code in (401, 403)

    def test_municipality_cannot_create(self, client, auth_headers_muni):
        r = client.post("/api/presets", json={
            "topic_code": "3",
            "preset_text": "לא מורשה",
            "category": "other",
        }, headers=auth_headers_muni)
        assert r.status_code in (401, 403)

    def test_missing_preset_text_returns_422(self, client, auth_headers_admin):
        r = client.post("/api/presets", json={
            "topic_code": "3",
            "category": "increase",
        }, headers=auth_headers_admin)
        assert r.status_code == 422


class TestUpdatePreset:
    def test_admin_can_update_text(self, client, db, admin_user, auth_headers_admin):
        p = seed_preset(db, admin_user)
        r = client.patch(f"/api/presets/{p.id}", json={
            "preset_text": "טקסט מעודכן",
        }, headers=auth_headers_admin)
        assert r.status_code == 200
        assert r.json()["preset_text"] == "טקסט מעודכן"

    def test_admin_can_deactivate(self, client, db, admin_user, auth_headers_admin):
        p = seed_preset(db, admin_user)
        r = client.patch(f"/api/presets/{p.id}", json={"is_active": False}, headers=auth_headers_admin)
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_update_nonexistent_returns_404(self, client, auth_headers_admin):
        r = client.patch("/api/presets/99999", json={"preset_text": "x"}, headers=auth_headers_admin)
        assert r.status_code == 404

    def test_employee_cannot_update(self, client, db, admin_user, auth_headers_emp):
        p = seed_preset(db, admin_user)
        r = client.patch(f"/api/presets/{p.id}", json={"preset_text": "hack"}, headers=auth_headers_emp)
        assert r.status_code in (401, 403)


class TestDeletePreset:
    def test_admin_can_delete(self, client, db, admin_user, auth_headers_admin):
        p = seed_preset(db, admin_user)
        r = client.delete(f"/api/presets/{p.id}", headers=auth_headers_admin)
        assert r.status_code in (200, 204)

    def test_delete_nonexistent_returns_404(self, client, auth_headers_admin):
        r = client.delete("/api/presets/99999", headers=auth_headers_admin)
        assert r.status_code == 404

    def test_employee_cannot_delete(self, client, db, admin_user, auth_headers_emp):
        p = seed_preset(db, admin_user)
        r = client.delete(f"/api/presets/{p.id}", headers=auth_headers_emp)
        assert r.status_code in (401, 403)
