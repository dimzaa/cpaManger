"""Student-count delta engine.

For every ministry code whose amount is driven by pupil count, this service
compares a budget line against the most recent prior run for the same
(municipality, topic_code, period_month) and reports how much of the amount
variance the pupil-count delta explains.

Background
----------
The Israeli Ministry of Education's מצבת תלמידים roster is the authoritative
input to the funding formulas: authorities upload student rosters by the 25th
of each month; on-time entries get paid for that month, late ones roll to the
next. Funding for codes such as 003 (שכל"מ גני ילדים), 052 (הסעות),
and several חינוך מיוחד / חטיבה עליונה items scales linearly with the count
on the cut-off date, so a change in the count is the dominant variance driver
month-over-month — which is exactly what this engine surfaces.

References:
- https://pob.education.gov.il/students/students-list/
- https://pob.education.gov.il/students/pupilsdata/
- https://pob.education.gov.il/institutions/main-kindergartens/kindergartens-reports/
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from backend.models.budget_line import BudgetLine
from backend.models.monthly_run import MonthlyRun


@dataclass
class StudentCountDelta:
    prev_run_id: int
    prev_num_children: int
    curr_num_children: int
    delta_children: int
    prev_amount: float
    curr_amount: float
    delta_amount: float
    # prev_amount * (curr / prev) — 0 when prev count is 0.
    expected_amount_from_count: float
    # expected - prev = the part of delta_amount explained by count.
    explained_amount: float
    # explained / delta_amount; None when delta_amount == 0.
    explained_ratio: Optional[float]
    # delta_amount - explained_amount.
    residual_amount: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_student_count_delta(
    db: Session,
    current_run_id: int,
    municipality_id: int,
    topic_code: str,
    period_month: str,
) -> Optional[StudentCountDelta]:
    """Compute the student-count delta for one budget line.

    Comparison is to the most recent prior run for the *same* ``period_month``
    (not ``current_month`` — that's the retro case handled elsewhere).

    Returns None when any of the following is true:
    - No prior run exists for this (municipality, period_month).
    - Either the prior or current ``num_children`` is missing (None).
    - No current budget line for the (run, municipality, topic_code, period).

    Zero is a real, meaningful value — only None means unknown.
    """
    topic_code = str(topic_code).strip()

    curr_run = db.query(MonthlyRun).filter(MonthlyRun.id == current_run_id).first()
    if not curr_run:
        return None

    curr_line = (
        db.query(BudgetLine)
        .filter(
            BudgetLine.run_id == current_run_id,
            BudgetLine.municipality_id == municipality_id,
            BudgetLine.topic_code == topic_code,
            BudgetLine.period_month == period_month,
        )
        .first()
    )
    if not curr_line:
        return None
    if curr_line.num_children is None:
        return None

    # Find the most recent prior run for this municipality that carries a
    # budget line for this (topic_code, period_month). "Most recent prior"
    # is ordered by uploaded_at DESC among runs whose id != current.
    prior_line = (
        db.query(BudgetLine)
        .join(MonthlyRun, BudgetLine.run_id == MonthlyRun.id)
        .filter(
            BudgetLine.municipality_id == municipality_id,
            BudgetLine.topic_code == topic_code,
            BudgetLine.period_month == period_month,
            BudgetLine.run_id != current_run_id,
            MonthlyRun.uploaded_at < curr_run.uploaded_at,
        )
        .order_by(MonthlyRun.uploaded_at.desc())
        .first()
    )
    if not prior_line:
        return None
    if prior_line.num_children is None:
        return None

    prev_count = int(prior_line.num_children)
    curr_count = int(curr_line.num_children)
    prev_amount = float(prior_line.amount or 0.0)
    curr_amount = float(curr_line.amount or 0.0)

    delta_children = curr_count - prev_count
    delta_amount = curr_amount - prev_amount

    if prev_count == 0:
        expected = 0.0
    else:
        expected = prev_amount * (curr_count / prev_count)

    explained = expected - prev_amount

    if delta_amount == 0:
        explained_ratio: Optional[float] = None
    else:
        explained_ratio = explained / delta_amount

    residual = delta_amount - explained

    return StudentCountDelta(
        prev_run_id=int(prior_line.run_id),
        prev_num_children=prev_count,
        curr_num_children=curr_count,
        delta_children=delta_children,
        prev_amount=prev_amount,
        curr_amount=curr_amount,
        delta_amount=delta_amount,
        expected_amount_from_count=expected,
        explained_amount=explained,
        explained_ratio=explained_ratio,
        residual_amount=residual,
    )
