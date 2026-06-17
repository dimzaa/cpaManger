"""Thresholds for the student-count delta / variance-driver classifier.

These numbers are policy knobs — tune them here rather than in service code.

Background
----------
The Israeli Ministry of Education runs the מצבת תלמידים roster system: local
authorities upload their student roster via the authorities portal by the 25th
of each month; on-time children are paid for that month, late entries roll to
the following month. Because the roster is the authoritative input to the
funding formulas (hours and shekels allocated per institution based on who is
on the list at cut-off), a change in student count is the single most common
driver of month-over-month budget variance for codes like 003 (גני ילדים),
052 (הסעות), and several חינוך מיוחד / חטיבה עליונה codes that scale linearly
with pupils.

The classifier below answers the accountant's first question when a number
moves: *"did the number of children change, or did the formula change?"* —
see https://pob.education.gov.il/students/students-list/ and the חטיבה עליונה
reporting guide (פרק א — מצבת תלמידים) for the underlying reporting mechanics.
"""

# If at least this fraction of the amount delta is explained by the count
# delta, classify the driver as "student_count".
STUDENT_COUNT_DOMINANT_THRESHOLD = 0.80

# If at most this fraction of the amount delta is explained by the count
# delta, classify the driver as "formula_or_rate" — i.e. something else moved.
STUDENT_COUNT_NEGLIGIBLE_THRESHOLD = 0.20

# Driver labels (also used by the frontend badge colors).
DRIVER_STUDENT_COUNT = "student_count"
DRIVER_FORMULA_OR_RATE = "formula_or_rate"
DRIVER_MIXED = "mixed"


def classify_driver(explained_ratio, delta_children, delta_amount):
    """Return one of the DRIVER_* labels or None.

    - None when the engine has no signal (no prior run, unknown count, zero
      amount delta and zero count delta).
    - "student_count" when |ratio| >= STUDENT_COUNT_DOMINANT_THRESHOLD and the
      count actually moved.
    - "formula_or_rate" when |ratio| < STUDENT_COUNT_NEGLIGIBLE_THRESHOLD and
      the amount actually moved.
    - "mixed" for everything in between.
    """
    if delta_amount == 0 and delta_children == 0:
        return None
    if explained_ratio is None:
        # amount delta is zero but count moved — treat as student_count driver
        # only if count moved; otherwise nothing to classify.
        if delta_children != 0:
            return DRIVER_STUDENT_COUNT
        return None
    abs_ratio = abs(explained_ratio)
    if abs_ratio >= STUDENT_COUNT_DOMINANT_THRESHOLD and delta_children != 0:
        return DRIVER_STUDENT_COUNT
    if abs_ratio < STUDENT_COUNT_NEGLIGIBLE_THRESHOLD and delta_amount != 0:
        return DRIVER_FORMULA_OR_RATE
    return DRIVER_MIXED
