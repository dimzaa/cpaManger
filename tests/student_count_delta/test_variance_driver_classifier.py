"""Unit tests for the variance-driver classifier and Hebrew prefix builder."""

import pytest

from backend.services.student_count_delta import StudentCountDelta
from backend.services.variance_driver_classifier import (
    build_explanation_prefix,
    classify,
)
from backend.utils.variance_thresholds import (
    DRIVER_FORMULA_OR_RATE,
    DRIVER_MIXED,
    DRIVER_STUDENT_COUNT,
    classify_driver,
)


def _make_delta(
    prev_count=100,
    curr_count=120,
    prev_amount=100_000.0,
    curr_amount=120_000.0,
    expected=120_000.0,
    explained=20_000.0,
    explained_ratio=1.0,
):
    return StudentCountDelta(
        prev_run_id=1,
        prev_num_children=prev_count,
        curr_num_children=curr_count,
        delta_children=curr_count - prev_count,
        prev_amount=prev_amount,
        curr_amount=curr_amount,
        delta_amount=curr_amount - prev_amount,
        expected_amount_from_count=expected,
        explained_amount=explained,
        explained_ratio=explained_ratio,
        residual_amount=(curr_amount - prev_amount) - explained,
    )


class TestClassifyDriverThresholds:

    def test_none_delta_returns_none(self):
        assert classify(None) is None

    def test_no_movement_at_all_returns_none(self):
        assert classify_driver(explained_ratio=0.0, delta_children=0, delta_amount=0) is None

    def test_count_dominates_classifies_as_student_count(self):
        assert classify_driver(
            explained_ratio=0.95, delta_children=10, delta_amount=10_000
        ) == DRIVER_STUDENT_COUNT

    def test_exactly_at_dominant_threshold_classifies_as_student_count(self):
        assert classify_driver(
            explained_ratio=0.80, delta_children=10, delta_amount=10_000
        ) == DRIVER_STUDENT_COUNT

    def test_negligible_ratio_classifies_as_formula_or_rate(self):
        assert classify_driver(
            explained_ratio=0.10, delta_children=1, delta_amount=10_000
        ) == DRIVER_FORMULA_OR_RATE

    def test_zero_count_move_with_amount_move_is_formula_or_rate(self):
        assert classify_driver(
            explained_ratio=0.0, delta_children=0, delta_amount=10_000
        ) == DRIVER_FORMULA_OR_RATE

    def test_middle_ratio_classifies_as_mixed(self):
        assert classify_driver(
            explained_ratio=0.5, delta_children=5, delta_amount=10_000
        ) == DRIVER_MIXED

    def test_negative_ratio_is_absolute(self):
        assert classify_driver(
            explained_ratio=-0.95, delta_children=-10, delta_amount=-10_000
        ) == DRIVER_STUDENT_COUNT

    def test_count_moved_but_amount_unchanged_still_student_count(self):
        # explained_ratio=None signals "delta_amount == 0"; if the count
        # still moved, the engine treats that as student_count.
        assert classify_driver(
            explained_ratio=None, delta_children=5, delta_amount=0
        ) == DRIVER_STUDENT_COUNT


class TestBuildExplanationPrefix:

    def test_student_count_prefix_hebrew(self):
        delta = _make_delta()
        text = build_explanation_prefix(delta, DRIVER_STUDENT_COUNT)
        assert "מספר ילדים" in text
        assert "100" in text and "120" in text
        assert "+20" in text

    def test_formula_prefix_hebrew(self):
        delta = _make_delta(curr_count=100, expected=100_000.0, explained=0.0, explained_ratio=0.0)
        text = build_explanation_prefix(delta, DRIVER_FORMULA_OR_RATE)
        assert text == "מספר ילדים לא השתנה מהותית — השינוי נובע מגורם אחר."

    def test_mixed_prefix_hebrew(self):
        delta = _make_delta(curr_count=110, expected=110_000.0, explained=10_000.0, explained_ratio=0.5)
        text = build_explanation_prefix(delta, DRIVER_MIXED)
        assert "חלק מהשינוי" in text
        assert "100" in text and "110" in text
        assert "היתר" in text

    def test_none_delta_returns_empty(self):
        assert build_explanation_prefix(None, DRIVER_STUDENT_COUNT) == ""

    def test_none_driver_returns_empty(self):
        assert build_explanation_prefix(_make_delta(), None) == ""

    def test_student_count_with_none_ratio_shows_100_pct(self):
        delta = _make_delta(
            curr_count=120,
            curr_amount=100_000.0,  # amount unchanged
            expected=120_000.0,
            explained=20_000.0,
            explained_ratio=None,
        )
        text = build_explanation_prefix(delta, DRIVER_STUDENT_COUNT)
        assert "100%" in text
