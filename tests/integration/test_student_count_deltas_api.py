"""Integration tests for GET /api/budget/runs/{run_id}/student-count-deltas."""

from datetime import datetime, timedelta

from backend.models.budget_line import BudgetLine
from backend.models.monthly_run import MonthlyRun


def _seed_run(db, municipality_id, month, uploaded_at, status="processed"):
    run = MonthlyRun(
        municipality_id=municipality_id,
        month=month,
        year=int(month.split("-")[0]),
        uploaded_at=uploaded_at,
        status=status,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _seed_line(db, run_id, municipality_id, topic_code, period_month, amount, num_children, name="גני ילדים"):
    line = BudgetLine(
        run_id=run_id,
        municipality_id=municipality_id,
        budget_topic=name,
        topic_code=topic_code,
        amount=amount,
        period_month=period_month,
        current_month=period_month,
        num_children=num_children,
        line_type="regular",
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


class TestStudentCountDeltasEndpoint:

    def test_returns_404_when_run_missing(self, client, auth_headers_admin, municipality_record):
        r = client.get(
            "/api/budget/runs/999/student-count-deltas",
            params={"municipality_id": municipality_record.id},
            headers=auth_headers_admin,
        )
        assert r.status_code == 404

    def test_forbids_cross_municipality_access(
        self, client, db, auth_headers_muni, municipality_record
    ):
        # Create another municipality the muni user doesn't belong to
        from backend.models.municipality import Municipality
        other = Municipality(name="עיר אחרת", code="OTHER1", login_email="other@test.com")
        db.add(other)
        db.commit()
        db.refresh(other)

        run = _seed_run(db, other.id, "2026-03", datetime.utcnow())
        r = client.get(
            f"/api/budget/runs/{run.id}/student-count-deltas",
            params={"municipality_id": other.id},
            headers=auth_headers_muni,
        )
        assert r.status_code == 403

    def test_returns_empty_when_no_prior_run(
        self, client, db, auth_headers_admin, municipality_record
    ):
        run = _seed_run(db, municipality_record.id, "2026-03", datetime.utcnow())
        _seed_line(db, run.id, municipality_record.id, "003", "2026-03", 120_000.0, 100)

        r = client.get(
            f"/api/budget/runs/{run.id}/student-count-deltas",
            params={"municipality_id": municipality_record.id},
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["run_id"] == run.id
        assert data["municipality_id"] == municipality_record.id
        assert data["previous_run_id"] is None
        assert data["lines"] == []

    def test_returns_deltas_sorted_by_absolute_amount_change(
        self, client, db, auth_headers_admin, municipality_record
    ):
        now = datetime.utcnow()
        prior = _seed_run(db, municipality_record.id, "2026-02", now - timedelta(days=30))
        curr = _seed_run(db, municipality_record.id, "2026-03", now)

        # Prior run — three codes
        _seed_line(db, prior.id, municipality_record.id, "003", "2026-02", 100_000.0, 100)
        _seed_line(db, prior.id, municipality_record.id, "052", "2026-02", 50_000.0, 50, name="הסעות")
        _seed_line(db, prior.id, municipality_record.id, "101", "2026-02", 10_000.0, 10, name="חינוך מיוחד")

        # Current run — 003 moves 20k, 052 moves 5k, 101 moves 2k
        _seed_line(db, curr.id, municipality_record.id, "003", "2026-02", 120_000.0, 120)
        _seed_line(db, curr.id, municipality_record.id, "052", "2026-02", 55_000.0, 55, name="הסעות")
        _seed_line(db, curr.id, municipality_record.id, "101", "2026-02", 12_000.0, 12, name="חינוך מיוחד")

        r = client.get(
            f"/api/budget/runs/{curr.id}/student-count-deltas",
            params={"municipality_id": municipality_record.id},
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["previous_run_id"] == prior.id
        assert len(data["lines"]) == 3
        # Sorted by |delta_amount| DESC: 20000 > 5000 > 2000
        assert data["lines"][0]["topic_code"] == "003"
        assert data["lines"][0]["delta_amount"] == 20_000.0
        assert data["lines"][0]["delta_children"] == 20
        assert data["lines"][0]["variance_driver"] == "student_count"
        assert data["lines"][1]["topic_code"] == "052"
        assert data["lines"][2]["topic_code"] == "101"

    def test_skips_lines_with_no_prior_count(
        self, client, db, auth_headers_admin, municipality_record
    ):
        now = datetime.utcnow()
        prior = _seed_run(db, municipality_record.id, "2026-02", now - timedelta(days=30))
        curr = _seed_run(db, municipality_record.id, "2026-03", now)

        _seed_line(db, prior.id, municipality_record.id, "003", "2026-02", 100_000.0, None)
        _seed_line(db, curr.id, municipality_record.id, "003", "2026-02", 120_000.0, 120)

        r = client.get(
            f"/api/budget/runs/{curr.id}/student-count-deltas",
            params={"municipality_id": municipality_record.id},
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        assert r.json()["lines"] == []

    def test_classifies_driver_types_correctly(
        self, client, db, auth_headers_admin, municipality_record
    ):
        now = datetime.utcnow()
        prior = _seed_run(db, municipality_record.id, "2026-02", now - timedelta(days=30))
        curr = _seed_run(db, municipality_record.id, "2026-03", now)

        # student_count: count moves, amount matches proportionally
        _seed_line(db, prior.id, municipality_record.id, "003", "2026-02", 100_000.0, 100)
        _seed_line(db, curr.id, municipality_record.id, "003", "2026-02", 120_000.0, 120)

        # formula_or_rate: count unchanged, amount moves
        _seed_line(db, prior.id, municipality_record.id, "052", "2026-02", 50_000.0, 50, name="הסעות")
        _seed_line(db, curr.id, municipality_record.id, "052", "2026-02", 55_000.0, 50, name="הסעות")

        # mixed: count +10%, amount +50% — only 20% explained
        _seed_line(db, prior.id, municipality_record.id, "101", "2026-02", 10_000.0, 10, name="חינוך מיוחד")
        _seed_line(db, curr.id, municipality_record.id, "101", "2026-02", 15_000.0, 11, name="חינוך מיוחד")

        r = client.get(
            f"/api/budget/runs/{curr.id}/student-count-deltas",
            params={"municipality_id": municipality_record.id},
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        by_code = {row["topic_code"]: row for row in r.json()["lines"]}
        assert by_code["003"]["variance_driver"] == "student_count"
        assert by_code["052"]["variance_driver"] == "formula_or_rate"
        assert by_code["101"]["variance_driver"] == "mixed"
