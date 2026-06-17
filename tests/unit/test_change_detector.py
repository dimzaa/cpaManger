"""
Unit tests for ChangeDetector service.
Tests change detection logic between budget lines — no DB, no HTTP.
"""

import pytest
from backend.services.change_detector import ChangeDetector, DetectedChange


@pytest.fixture
def detector():
    return ChangeDetector()


class TestDetectedChangeToDictFormat:
    def test_to_dict_has_required_keys(self):
        ch = DetectedChange(
            change_type="numeric",
            field_name="num_children",
            previous_value=10,
            current_value=15,
            impact_amount=5000.0,
            impact_pct=50.0,
            hebrew_description="מספר ילדים עלה",
        )
        d = ch.to_dict()
        for key in ("change_type", "field_name", "previous", "current",
                    "impact_shekel", "impact_pct", "hebrew_description"):
            assert key in d

    def test_to_dict_values_correct(self):
        ch = DetectedChange(
            change_type="numeric",
            field_name="num_children",
            previous_value=10,
            current_value=15,
            impact_amount=5000.0,
            impact_pct=50.0,
            hebrew_description="מספר ילדים עלה",
        )
        d = ch.to_dict()
        assert d["change_type"] == "numeric"
        assert d["impact_shekel"] == 5000.0
        assert d["hebrew_description"] == "מספר ילדים עלה"


class TestDetectChangesBasic:
    def test_returns_empty_list_for_identical_lines(self, detector):
        prev = {"num_children": 10, "cost_per_child": 1000}
        curr = {"num_children": 10, "cost_per_child": 1000}
        result = detector.detect_changes(prev, curr, "3")
        assert result == []

    def test_returns_empty_when_prev_is_none(self, detector):
        curr = {"num_children": 10}
        result = detector.detect_changes(None, curr, "3")
        assert result == []

    def test_returns_empty_when_curr_is_none(self, detector):
        prev = {"num_children": 10}
        result = detector.detect_changes(prev, None, "3")
        assert result == []

    def test_returns_empty_for_unknown_topic_code(self, detector):
        """Topic codes without CRITICAL_FIELDS produce no numeric changes."""
        prev = {"num_children": 10}
        curr = {"num_children": 20}
        result = detector.detect_changes(prev, curr, "999")
        assert result == []


class TestDetectNumericChanges:
    def test_detects_children_increase(self, detector):
        prev = {"num_children": 10, "cost_per_child": 1000}
        curr = {"num_children": 15, "cost_per_child": 1000}
        changes = detector.detect_changes(prev, curr, "3")
        assert len(changes) >= 1
        fields = [c.field_name for c in changes]
        assert "num_children" in fields

    def test_detects_children_decrease(self, detector):
        prev = {"num_children": 20, "cost_per_child": 1000}
        curr = {"num_children": 12, "cost_per_child": 1000}
        changes = detector.detect_changes(prev, curr, "3")
        child_changes = [c for c in changes if c.field_name == "num_children"]
        assert child_changes
        assert child_changes[0].previous_value == 20
        assert child_changes[0].current_value == 12

    def test_detects_cost_per_child_change(self, detector):
        prev = {"num_children": 10, "cost_per_child": 1000}
        curr = {"num_children": 10, "cost_per_child": 1200}
        changes = detector.detect_changes(prev, curr, "3")
        fields = [c.field_name for c in changes]
        assert "cost_per_child" in fields

    def test_impact_amount_calculated_for_children_change(self, detector):
        prev = {"num_children": 10, "cost_per_child": 1000}
        curr = {"num_children": 15, "cost_per_child": 1000}
        changes = detector.detect_changes(prev, curr, "3")
        child_ch = next(c for c in changes if c.field_name == "num_children")
        # 5 extra children × ₪1,000 = ₪5,000
        assert child_ch.impact_amount == pytest.approx(5000.0)

    def test_impact_pct_calculated(self, detector):
        prev = {"num_children": 10, "cost_per_child": 1000}
        curr = {"num_children": 15, "cost_per_child": 1000}
        changes = detector.detect_changes(prev, curr, "3")
        child_ch = next(c for c in changes if c.field_name == "num_children")
        assert child_ch.impact_pct == pytest.approx(50.0)

    def test_no_change_no_detection(self, detector):
        prev = {"num_children": 10, "cost_per_child": 1000, "participation_pct": 0.5}
        curr = {"num_children": 10, "cost_per_child": 1000, "participation_pct": 0.5}
        changes = detector.detect_changes(prev, curr, "3")
        assert changes == []

    def test_topic_19_detects_num_units(self, detector):
        prev = {"num_units": 5, "cost_per_unit": 2000}
        curr = {"num_units": 8, "cost_per_unit": 2000}
        changes = detector.detect_changes(prev, curr, "19")
        fields = [c.field_name for c in changes]
        assert "num_units" in fields

    def test_topic_50_transport_detects_children(self, detector):
        prev = {"num_children": 30, "cost_per_child": 500}
        curr = {"num_children": 25, "cost_per_child": 500}
        changes = detector.detect_changes(prev, curr, "50")
        fields = [c.field_name for c in changes]
        assert "num_children" in fields
