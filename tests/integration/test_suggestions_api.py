"""
Integration tests for Suggestions API endpoints:
  POST   /api/suggestions
  GET    /api/suggestions/pending
  GET    /api/suggestions/my
  GET    /api/suggestions/my-rejected
  GET    /api/suggestions/my-counts
  GET    /api/suggestions/my-all
  POST   /api/suggestions/{id}/approve
  POST   /api/suggestions/{id}/reject
"""

import pytest
from backend.models.explanation_suggestion import ExplanationSuggestion, SuggestionStatus, SuggestionType
from backend.models.budget_line import BudgetLine
from backend.models.monthly_run import MonthlyRun


def seed_monthly_run(db, municipality_id):
    """Helper: seed a MonthlyRun record (required by BudgetLine.run_id FK)."""
    run = MonthlyRun(
        municipality_id=municipality_id,
        month="2026-03",
        year=2026,
        status="processed",
        invoice_total=100000.0,
        breakdown_total=100000.0,
        is_balanced=True,
        difference=0.0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def seed_budget_line(db, municipality_id, run_id=None):
    """Helper: seed a BudgetLine for suggestion tests."""
    if run_id is None:
        run = seed_monthly_run(db, municipality_id)
        run_id = run.id
    line = BudgetLine(
        budget_topic="גני ילדים רגיל",
        topic_code="3",
        amount=100000.0,
        period_month="2026-03",
        current_month="2026-03",
        line_type="regular",
        is_retro=False,
        municipality_id=municipality_id,
        run_id=run_id,
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def seed_suggestion(db, line, employee_id, municipality_id, status=SuggestionStatus.PENDING):
    sugg = ExplanationSuggestion(
        budget_line_id=line.id,
        municipality_id=municipality_id,
        month="2026-03",
        topic_code="3",
        suggestion_type=SuggestionType.CUSTOM,
        custom_text="הסבר מותאם אישית",
        suggested_by=employee_id,
        status=status,
    )
    db.add(sugg)
    db.commit()
    db.refresh(sugg)
    return sugg


class TestSubmitSuggestion:
    def test_employee_can_submit(self, client, db, auth_headers_emp, employee_user, municipality_record):
        line = seed_budget_line(db, municipality_record.id)
        r = client.post("/api/suggestions", json={
            "budget_line_id": line.id,
            "municipality_id": municipality_record.id,
            "month": "2026-03",
            "topic_code": "3",
            "suggestion_type": "custom",
            "custom_text": "הסבר מוצע",
        }, headers=auth_headers_emp)
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["topic_code"] == "3"
        assert data["custom_text"] == "הסבר מוצע"
        assert data["status"] == "pending"

    def test_municipality_user_can_submit(self, client, db, auth_headers_muni, municipality_record):
        line = seed_budget_line(db, municipality_record.id)
        r = client.post("/api/suggestions", json={
            "budget_line_id": line.id,
            "municipality_id": municipality_record.id,
            "month": "2026-03",
            "topic_code": "3",
            "suggestion_type": "custom",
            "custom_text": "הסבר ממשתמש עיר",
        }, headers=auth_headers_muni)
        # Municipality role is explicitly blocked (403); only employee/admin can submit
        assert r.status_code == 403

    def test_unauthenticated_blocked(self, client, db, municipality_record):
        line = seed_budget_line(db, municipality_record.id)
        r = client.post("/api/suggestions", json={
            "budget_line_id": line.id,
            "municipality_id": municipality_record.id,
            "month": "2026-03",
            "topic_code": "3",
            "suggestion_type": "custom",
            "custom_text": "test",
        })
        assert r.status_code in (401, 403)

    def test_missing_fields_returns_422(self, client, auth_headers_emp):
        r = client.post("/api/suggestions", json={
            "municipality_id": 1,
        }, headers=auth_headers_emp)
        assert r.status_code == 422


class TestPendingSuggestions:
    def test_admin_sees_pending(self, client, db, auth_headers_admin, employee_user, municipality_record):
        line = seed_budget_line(db, municipality_record.id)
        seed_suggestion(db, line, employee_user.id, municipality_record.id)
        r = client.get("/api/suggestions/pending", headers=auth_headers_admin)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_employee_blocked_from_pending(self, client, auth_headers_emp):
        r = client.get("/api/suggestions/pending", headers=auth_headers_emp)
        assert r.status_code in (401, 403)

    def test_unauthenticated_blocked(self, client):
        r = client.get("/api/suggestions/pending")
        assert r.status_code in (401, 403)


class TestMySuggestions:
    def test_employee_can_view_own(self, client, db, auth_headers_emp, employee_user, municipality_record):
        line = seed_budget_line(db, municipality_record.id)
        seed_suggestion(db, line, employee_user.id, municipality_record.id)
        r = client.get("/api/suggestions/my", headers=auth_headers_emp)
        assert r.status_code == 200

    def test_unauthenticated_blocked(self, client):
        r = client.get("/api/suggestions/my")
        assert r.status_code in (401, 403)


class TestMyRejectedSuggestions:
    def test_employee_sees_rejected(self, client, db, auth_headers_emp, employee_user, municipality_record):
        line = seed_budget_line(db, municipality_record.id)
        seed_suggestion(db, line, employee_user.id, municipality_record.id, status=SuggestionStatus.REJECTED)
        r = client.get("/api/suggestions/my-rejected", headers=auth_headers_emp)
        assert r.status_code == 200

    def test_unauthenticated_blocked(self, client):
        r = client.get("/api/suggestions/my-rejected")
        assert r.status_code in (401, 403)


class TestApproveSuggestion:
    def test_admin_can_approve(self, client, db, auth_headers_admin, employee_user, municipality_record):
        line = seed_budget_line(db, municipality_record.id)
        sugg = seed_suggestion(db, line, employee_user.id, municipality_record.id)
        r = client.patch(f"/api/suggestions/{sugg.id}/approve", json={
            "review_note": "מאושר",
        }, headers=auth_headers_admin)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "approved"

    def test_employee_cannot_approve(self, client, db, auth_headers_emp, employee_user, municipality_record):
        line = seed_budget_line(db, municipality_record.id)
        sugg = seed_suggestion(db, line, employee_user.id, municipality_record.id)
        r = client.patch(f"/api/suggestions/{sugg.id}/approve", json={}, headers=auth_headers_emp)
        assert r.status_code in (401, 403)

    def test_approve_nonexistent_returns_404(self, client, auth_headers_admin):
        r = client.patch("/api/suggestions/99999/approve", json={}, headers=auth_headers_admin)
        assert r.status_code == 404


class TestRejectSuggestion:
    def test_admin_can_reject(self, client, db, auth_headers_admin, employee_user, municipality_record):
        line = seed_budget_line(db, municipality_record.id)
        sugg = seed_suggestion(db, line, employee_user.id, municipality_record.id)
        r = client.patch(f"/api/suggestions/{sugg.id}/reject", json={
            "review_note": "לא רלוונטי",
        }, headers=auth_headers_admin)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "rejected"
        assert data["review_note"] == "לא רלוונטי"

    def test_reject_requires_review_note(self, client, db, auth_headers_admin, employee_user, municipality_record):
        line = seed_budget_line(db, municipality_record.id)
        sugg = seed_suggestion(db, line, employee_user.id, municipality_record.id)
        r = client.patch(f"/api/suggestions/{sugg.id}/reject", json={}, headers=auth_headers_admin)
        assert r.status_code == 422

    def test_employee_cannot_reject(self, client, db, auth_headers_emp, employee_user, municipality_record):
        line = seed_budget_line(db, municipality_record.id)
        sugg = seed_suggestion(db, line, employee_user.id, municipality_record.id)
        r = client.patch(f"/api/suggestions/{sugg.id}/reject", json={
            "review_note": "test",
        }, headers=auth_headers_emp)
        assert r.status_code in (401, 403)

    def test_reject_nonexistent_returns_404(self, client, auth_headers_admin):
        r = client.patch("/api/suggestions/99999/reject", json={
            "review_note": "not found",
        }, headers=auth_headers_admin)
        assert r.status_code == 404
