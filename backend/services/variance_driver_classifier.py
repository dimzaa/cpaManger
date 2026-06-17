"""Classify the variance driver for a budget line based on its student-count
delta, and produce the Hebrew prefix sentence that gets prepended to the
explanation.

Keeps all driver-related logic in one place so ``change_detector`` and the
various explanation generators don't each re-implement it.
"""

from __future__ import annotations

from typing import Optional

from backend.services.student_count_delta import StudentCountDelta
from backend.utils.variance_thresholds import (
    DRIVER_FORMULA_OR_RATE,
    DRIVER_MIXED,
    DRIVER_STUDENT_COUNT,
    classify_driver,
)


def _format_signed_int(value: int) -> str:
    return f"+{value}" if value > 0 else f"{value}"


def _format_signed_shekel(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}₪{abs(value):,.0f}"


def classify(delta: Optional[StudentCountDelta]) -> Optional[str]:
    """Return one of the driver labels or None for the given delta."""
    if delta is None:
        return None
    return classify_driver(
        explained_ratio=delta.explained_ratio,
        delta_children=delta.delta_children,
        delta_amount=delta.delta_amount,
    )


def build_explanation_prefix(delta: Optional[StudentCountDelta], driver: Optional[str]) -> str:
    """Hebrew one-liner prepended to the full explanation. Empty string when
    there is nothing meaningful to say.
    """
    if delta is None or driver is None:
        return ""

    if driver == DRIVER_STUDENT_COUNT:
        signed_delta = _format_signed_int(delta.delta_children)
        signed_expl = _format_signed_shekel(delta.explained_amount)
        signed_actual = _format_signed_shekel(delta.delta_amount)
        if delta.explained_ratio is None:
            ratio_pct = 100 if delta.delta_children != 0 else 0
        else:
            ratio_pct = round(abs(delta.explained_ratio) * 100)
        return (
            f"מספר ילדים: {delta.prev_num_children} → {delta.curr_num_children} "
            f"({signed_delta}). השפעה משוערת על הסכום: {signed_expl} ₪ "
            f"מתוך {signed_actual} ₪ ({ratio_pct}%)."
        )

    if driver == DRIVER_FORMULA_OR_RATE:
        return "מספר ילדים לא השתנה מהותית — השינוי נובע מגורם אחר."

    if driver == DRIVER_MIXED:
        signed_delta = _format_signed_int(delta.delta_children)
        return (
            f"חלק מהשינוי נובע משינוי במספר ילדים "
            f"({delta.prev_num_children} → {delta.curr_num_children}, {signed_delta}); "
            f"היתר נובע מגורם אחר."
        )

    return ""
