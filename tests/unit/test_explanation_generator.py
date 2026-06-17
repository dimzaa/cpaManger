"""
Unit tests for ExplanationGenerator service.
Pure-logic tests — no DB, no HTTP.
"""

import pytest
from backend.services.explanation_generator import ExplanationGenerator


class TestGenerateForRegularLine:
    def test_returns_string(self):
        result = ExplanationGenerator.generate_for_regular_line(
            topic_code="3",
            topic_name="ילדי חינוך מיוחד",
            amount=50000,
            month="2026-03",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_includes_topic_name_in_output(self):
        result = ExplanationGenerator.generate_for_regular_line(
            topic_code="3",
            topic_name="ילדי חינוך מיוחד",
            amount=50000,
            month="2026-03",
        )
        assert "ילדי חינוך מיוחד" in result

    def test_increase_vs_previous_month(self):
        result = ExplanationGenerator.generate_for_regular_line(
            topic_code="3",
            topic_name="ילדי חינוך מיוחד",
            amount=100000,
            month="2026-03",
            previous_month_amount=80000,
        )
        # Should mention increase (~25%)
        assert "גדול" in result or "עלה" in result or "%" in result

    def test_decrease_vs_previous_month(self):
        result = ExplanationGenerator.generate_for_regular_line(
            topic_code="3",
            topic_name="ילדי חינוך מיוחד",
            amount=60000,
            month="2026-03",
            previous_month_amount=80000,
        )
        assert "קטן" in result or "ירד" in result or "%" in result

    def test_no_previous_month_no_comparison(self):
        result = ExplanationGenerator.generate_for_regular_line(
            topic_code="19",
            topic_name="עוזרות גננות",
            amount=40000,
            month="2026-03",
        )
        # Should not mention comparison words
        assert "%" not in result or "גדול" not in result


class TestGenerateForRetroLine:
    def test_returns_string(self):
        result = ExplanationGenerator.generate_for_retro_line(
            topic_code="3",
            topic_name="ילדי חינוך מיוחד",
            amount=15000,
            period_month="2026-01",
            current_month="2026-03",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_retro_indicator(self):
        result = ExplanationGenerator.generate_for_retro_line(
            topic_code="3",
            topic_name="ילדי חינוך מיוחד",
            amount=15000,
            period_month="2026-01",
            current_month="2026-03",
        )
        # Should mention retro / backwards payment
        assert "רטרו" in result or "קודם" in result or "ינואר" in result
