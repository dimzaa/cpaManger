from datetime import datetime

from backend.models.monthly_run import MonthlyRun
from backend.models.user import AuditLog


def seed_run(db, municipality_id, month="2026-03"):
    run = MonthlyRun(
        municipality_id=municipality_id,
        month=month,
        year=int(month[:4]),
        status="processed",
        invoice_total=100000,
        breakdown_total=105000,
        is_balanced=False,
        difference=5000,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


class TestRunReviewStatusPatch:
    def test_patch_as_admin_updates_reviewed_and_sets_timestamp(
        self, client, db, auth_headers_admin, municipality_record
    ):
        run = seed_run(db, municipality_record.id)

        r = client.patch(
            f"/api/admin/runs/{run.id}/review-status",
            json={"status": "reviewed", "note": "נסגר"},
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["review_status"] == "reviewed"
        assert data["review_status_note"] == "נסגר"
        assert data["reviewed_by_user_id"] is not None
        assert data["reviewed_at"] is not None

    def test_patch_as_municipality_user_forbidden(
        self, client, db, auth_headers_muni, municipality_record
    ):
        run = seed_run(db, municipality_record.id)

        r = client.patch(
            f"/api/admin/runs/{run.id}/review-status",
            json={"status": "in_review", "note": ""},
            headers=auth_headers_muni,
        )
        assert r.status_code == 403

    def test_patch_invalid_status_rejected(
        self, client, db, auth_headers_admin, municipality_record
    ):
        run = seed_run(db, municipality_record.id)

        r = client.patch(
            f"/api/admin/runs/{run.id}/review-status",
            json={"status": "bad_status", "note": "x"},
            headers=auth_headers_admin,
        )
        assert r.status_code in (400, 422)

    def test_flagged_requires_non_empty_note(
        self, client, db, auth_headers_admin, municipality_record
    ):
        run = seed_run(db, municipality_record.id)

        r = client.patch(
            f"/api/admin/runs/{run.id}/review-status",
            json={"status": "flagged", "note": "   "},
            headers=auth_headers_admin,
        )
        assert r.status_code == 400

    def test_transition_reviewed_to_pending_clears_review_fields(
        self, client, db, auth_headers_admin, municipality_record
    ):
        run = seed_run(db, municipality_record.id)

        first = client.patch(
            f"/api/admin/runs/{run.id}/review-status",
            json={"status": "reviewed", "note": "נבדק"},
            headers=auth_headers_admin,
        )
        assert first.status_code == 200
        assert first.json()["reviewed_at"] is not None

        second = client.patch(
            f"/api/admin/runs/{run.id}/review-status",
            json={"status": "pending", "note": ""},
            headers=auth_headers_admin,
        )
        assert second.status_code == 200
        data = second.json()
        assert data["review_status"] == "pending"
        assert data["reviewed_at"] is None
        assert data["reviewed_by_user_id"] is None

    def test_audit_log_entry_written(
        self, client, db, auth_headers_admin, admin_user, municipality_record
    ):
        run = seed_run(db, municipality_record.id)

        r = client.patch(
            f"/api/admin/runs/{run.id}/review-status",
            json={"status": "in_review", "note": ""},
            headers=auth_headers_admin,
        )
        assert r.status_code == 200

        audit = (
            db.query(AuditLog)
            .filter(AuditLog.user_id == admin_user.id, AuditLog.action == "update_review_status")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert audit is not None
        assert audit.resource_type == "monthly_run"
        assert audit.resource_id == run.id
