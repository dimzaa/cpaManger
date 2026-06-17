"""Unit tests for the student-count delta engine.

The engine compares a budget line against the most recent prior run for the
same (municipality, topic_code, period_month) and reports how much of the
amount variance is explained by the pupil-count move.
"""

from datetime import datetime, timedelta

import pytest

from backend.models.budget_line import BudgetLine
from backend.models.monthly_run import MonthlyRun
from backend.services.student_count_delta import (
    StudentCountDelta,
    compute_student_count_delta,
)


def _make_run(db, municipality_id, month, uploaded_at):
    run = MonthlyRun(
        municipality_id=municipality_id,
        month=month,
        year=int(month.split("-")[0]),
        uploaded_at=uploaded_at,
        status="processed",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _make_line(db, run_id, municipality_id, topic_code, period_month, amount, num_children):
    line = BudgetLine(
        run_id=run_id,
        municipality_id=municipality_id,
        budget_topic="גני ילדים",
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


class TestComputeStudentCountDelta:

    def test_returns_none_when_no_prior_run(self, db, municipality_record):
        now = datetime.utcnow()
        run = _make_run(db, municipality_record.id, "2026-03", now)
        _make_line(db, run.id, municipality_record.id, "003", "2026-03", 120_000.0, 100)

        result = compute_student_count_delta(
            db, run.id, municipality_record.id, "003", "2026-03"
        )
        assert result is None

    def test_pupil_count_dominates_amount_move(self, db, municipality_record):
        now = datetime.utcnow()
        prior = _make_run(db, municipality_record.id, "2026-02", now - timedelta(days=30))
        curr = _make_run(db, municipality_record.id, "2026-03", now)

        _make_line(db, prior.id, municipality_record.id, "003", "2026-02", 100_000.0, 100)
        _make_line(db, curr.id, municipality_record.id, "003", "2026-02", 120_000.0, 120)

        result = compute_student_count_delta(
            db, curr.id, municipality_record.id, "003", "2026-02"
        )
        assert result is not None
        assert isinstance(result, StudentCountDelta)
        assert result.prev_num_children == 100
        assert result.curr_num_children == 120
        assert result.delta_children == 20
        assert result.delta_amount == pytest.approx(20_000.0)
        # expected = 100000 * 120/100 = 120000, so explained = 20000
        assert result.expected_amount_from_count == pytest.approx(120_000.0)
        assert result.explained_amount == pytest.approx(20_000.0)
        assert result.explained_ratio == pytest.approx(1.0)
        assert result.residual_amount == pytest.approx(0.0)

    def test_rate_change_no_count_move(self, db, municipality_record):
        now = datetime.utcnow()
        prior = _make_run(db, municipality_record.id, "2026-02", now - timedelta(days=30))
        curr = _make_run(db, municipality_record.id, "2026-03", now)

        _make_line(db, prior.id, municipality_record.id, "003", "2026-02", 100_000.0, 100)
        _make_line(db, curr.id, municipality_record.id, "003", "2026-02", 110_000.0, 100)

        result = compute_student_count_delta(
            db, curr.id, municipality_record.id, "003", "2026-02"
        )
        assert result is not None
        assert result.delta_children == 0
        assert result.delta_amount == pytest.approx(10_000.0)
        assert result.explained_amount == pytest.approx(0.0)
        assert result.explained_ratio == pytest.approx(0.0)
        assert result.residual_amount == pytest.approx(10_000.0)

    def test_mixed_driver_partial_explanation(self, db, municipality_record):
        now = datetime.utcnow()
        prior = _make_run(db, municipality_record.id, "2026-02", now - timedelta(days=30))
        curr = _make_run(db, municipality_record.id, "2026-03", now)

        _make_line(db, prior.id, municipality_record.id, "003", "2026-02", 100_000.0, 100)
        # Count moves +10% (to 110) but amount moves +20% (to 120000) —
        # only half is explained by count.
        _make_line(db, curr.id, municipality_record.id, "003", "2026-02", 120_000.0, 110)

        result = compute_student_count_delta(
            db, curr.id, municipality_record.id, "003", "2026-02"
        )
        assert result is not None
        assert result.delta_children == 10
        assert result.delta_amount == pytest.approx(20_000.0)
        assert result.expected_amount_from_count == pytest.approx(110_000.0)
        assert result.explained_amount == pytest.approx(10_000.0)
        assert result.explained_ratio == pytest.approx(0.5)
        assert result.residual_amount == pytest.approx(10_000.0)

    def test_zero_num_children_is_treated_as_real_value(self, db, municipality_record):
        now = datetime.utcnow()
        prior = _make_run(db, municipality_record.id, "2026-02", now - timedelta(days=30))
        curr = _make_run(db, municipality_record.id, "2026-03", now)

        _make_line(db, prior.id, municipality_record.id, "003", "2026-02", 50_000.0, 50)
        _make_line(db, curr.id, municipality_record.id, "003", "2026-02", 0.0, 0)

        result = compute_student_count_delta(
            db, curr.id, municipality_record.id, "003", "2026-02"
        )
        assert result is not None
        assert result.prev_num_children == 50
        assert result.curr_num_children == 0
        assert result.delta_children == -50
        assert result.delta_amount == pytest.approx(-50_000.0)

    def test_none_num_children_returns_none(self, db, municipality_record):
        now = datetime.utcnow()
        prior = _make_run(db, municipality_record.id, "2026-02", now - timedelta(days=30))
        curr = _make_run(db, municipality_record.id, "2026-03", now)

        _make_line(db, prior.id, municipality_record.id, "003", "2026-02", 50_000.0, None)
        _make_line(db, curr.id, municipality_record.id, "003", "2026-02", 60_000.0, 60)

        result = compute_student_count_delta(
            db, curr.id, municipality_record.id, "003", "2026-02"
        )
        assert result is None

    def test_prev_count_zero_makes_expected_zero(self, db, municipality_record):
        now = datetime.utcnow()
        prior = _make_run(db, municipality_record.id, "2026-02", now - timedelta(days=30))
        curr = _make_run(db, municipality_record.id, "2026-03", now)

        _make_line(db, prior.id, municipality_record.id, "003", "2026-02", 0.0, 0)
        _make_line(db, curr.id, municipality_record.id, "003", "2026-02", 50_000.0, 50)

        result = compute_student_count_delta(
            db, curr.id, municipality_record.id, "003", "2026-02"
        )
        assert result is not None
        assert result.expected_amount_from_count == pytest.approx(0.0)
        assert result.explained_amount == pytest.approx(0.0)
        assert result.residual_amount == pytest.approx(50_000.0)

    def test_picks_most_recent_prior_run(self, db, municipality_record):
        now = datetime.utcnow()
        oldest = _make_run(db, municipality_record.id, "2026-02", now - timedelta(days=60))
        middle = _make_run(db, municipality_record.id, "2026-02", now - timedelta(days=30))
        curr = _make_run(db, municipality_record.id, "2026-02", now)

        _make_line(db, oldest.id, municipality_record.id, "003", "2026-02", 50_000.0, 50)
        _make_line(db, middle.id, municipality_record.id, "003", "2026-02", 100_000.0, 100)
        _make_line(db, curr.id, municipality_record.id, "003", "2026-02", 110_000.0, 110)

        result = compute_student_count_delta(
            db, curr.id, municipality_record.id, "003", "2026-02"
        )
        assert result is not None
        # Must compare against middle (most recent prior), not oldest.
        assert result.prev_run_id == middle.id
        assert result.prev_num_children == 100

    def test_compares_same_period_month_only(self, db, municipality_record):
        """If prior run's line was for a different period_month, it shouldn't match."""
        now = datetime.utcnow()
        prior = _make_run(db, municipality_record.id, "2026-01", now - timedelta(days=30))
        curr = _make_run(db, municipality_record.id, "2026-03", now)

        _make_line(db, prior.id, municipality_record.id, "003", "2026-01", 50_000.0, 50)
        _make_line(db, curr.id, municipality_record.id, "003", "2026-02", 60_000.0, 60)

        result = compute_student_count_delta(
            db, curr.id, municipality_record.id, "003", "2026-02"
        )
        assert result is None

    def test_zero_amount_delta_returns_none_explained_ratio(self, db, municipality_record):
        now = datetime.utcnow()
        prior = _make_run(db, municipality_record.id, "2026-02", now - timedelta(days=30))
        curr = _make_run(db, municipality_record.id, "2026-03", now)

        _make_line(db, prior.id, municipality_record.id, "003", "2026-02", 50_000.0, 50)
        _make_line(db, curr.id, municipality_record.id, "003", "2026-02", 50_000.0, 55)

        result = compute_student_count_delta(
            db, curr.id, municipality_record.id, "003", "2026-02"
        )
        assert result is not None
        assert result.delta_amount == pytest.approx(0.0)
        assert result.explained_ratio is None
