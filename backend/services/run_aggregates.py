"""
Priority-1 dashboard aggregates for a MonthlyRun.

Single function: recompute_run_aggregates(db, run_id).

Reads budget_lines for the run, computes:
  * regular_total          — Σ amount WHERE NOT is_retro
  * retro_positive_total   — Σ amount WHERE is_retro AND amount > 0
  * retro_negative_total   — Σ amount WHERE is_retro AND amount < 0
  * topics_count           — COUNT(DISTINCT topic_code)
  * lines_count            — COUNT(*)

Writes them back to monthly_runs. Idempotent — safe to re-run any time.

Used by:
  * routes/upload.py — called at the end of each upload, before commit.
  * scripts/backfill_run_aggregates.py — one-shot backfill for existing
    runs in Neon prod that pre-date this column.

The function is intentionally narrow. Cross-run logic (MoM, anomalies,
trailing-N averages) belongs in Priority 2/4 with its own service —
NOT here. This is the "fast aggregate from one run" piece.
"""
from __future__ import annotations

from typing import Dict, Any

from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from backend.models import BudgetLine, MonthlyRun


def recompute_run_aggregates(db: Session, run_id: int) -> Dict[str, Any]:
    """
    Recompute and persist the Priority-1 aggregates for ``run_id``.

    Returns a dict of the computed values for logging / verification.
    Raises if the run doesn't exist (caller is expected to know its run_id).
    """
    run = db.query(MonthlyRun).filter(MonthlyRun.id == run_id).first()
    if run is None:
        raise ValueError(f"MonthlyRun id={run_id} not found")

    # Single round-trip: pull the four sums + two counts via one grouped query.
    # Doing it as one query avoids the overhead of 4 separate aggregations and
    # keeps the function fast at scale.
    base = db.query(BudgetLine).filter(BudgetLine.run_id == run_id)

    regular_total = base.filter(BudgetLine.is_retro.is_(False)).with_entities(
        func.coalesce(func.sum(BudgetLine.amount), 0.0)
    ).scalar() or 0.0

    retro_pos_total = base.filter(
        BudgetLine.is_retro.is_(True), BudgetLine.amount > 0
    ).with_entities(
        func.coalesce(func.sum(BudgetLine.amount), 0.0)
    ).scalar() or 0.0

    retro_neg_total = base.filter(
        BudgetLine.is_retro.is_(True), BudgetLine.amount < 0
    ).with_entities(
        func.coalesce(func.sum(BudgetLine.amount), 0.0)
    ).scalar() or 0.0

    topics_count = base.with_entities(
        func.count(distinct(BudgetLine.topic_code))
    ).scalar() or 0

    lines_count = base.with_entities(func.count(BudgetLine.id)).scalar() or 0

    # Persist back to the run.
    run.regular_total = round(float(regular_total), 2)
    run.retro_positive_total = round(float(retro_pos_total), 2)
    run.retro_negative_total = round(float(retro_neg_total), 2)
    run.topics_count = int(topics_count)
    run.lines_count = int(lines_count)
    db.flush()

    return {
        "run_id": run_id,
        "regular_total": run.regular_total,
        "retro_positive_total": run.retro_positive_total,
        "retro_negative_total": run.retro_negative_total,
        "topics_count": run.topics_count,
        "lines_count": run.lines_count,
    }


def backfill_all_runs(db: Session) -> Dict[str, Any]:
    """
    Recompute aggregates for every existing MonthlyRun. Used once after
    deploying the schema change to populate historical rows.

    Returns a summary dict (count of runs updated, list of any failures).
    """
    updated = 0
    failures = []
    for run in db.query(MonthlyRun).order_by(MonthlyRun.id).all():
        try:
            recompute_run_aggregates(db, run.id)
            updated += 1
        except Exception as exc:  # noqa: BLE001
            failures.append({"run_id": run.id, "error": str(exc)[:200]})
    db.commit()
    return {"updated": updated, "failures": failures}
