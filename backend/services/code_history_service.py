"""
CodeHistory service — Priority 3.

recompute_code_history_for_run(db, run_id) — for each topic_code in this
run, upsert one row into code_history keyed by (muni_id, topic_code,
year_month). Idempotent: deletes existing rows for this (muni, year_month)
before inserting, so re-uploading the same month overwrites cleanly.

The year_month is taken from MonthlyRun.month (already 'YYYY-MM' format).
"""
from __future__ import annotations

from typing import Dict, Any

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from backend.models import BudgetLine, MonthlyRun, CodeHistory


def recompute_code_history_for_run(db: Session, run_id: int) -> Dict[str, Any]:
    run = db.query(MonthlyRun).filter(MonthlyRun.id == run_id).first()
    if run is None:
        raise ValueError(f"MonthlyRun id={run_id} not found")

    muni_id = run.municipality_id
    year_month = run.month

    # Idempotent wipe: any existing rows for this (muni, year_month) get
    # replaced. We deliberately scope to this (muni, year_month) — NOT just
    # this run_id — because re-uploading the same month creates a new
    # monthly_run record with different id, but the history row should still
    # be unique per (muni, month).
    db.query(CodeHistory).filter(
        CodeHistory.municipality_id == muni_id,
        CodeHistory.year_month == year_month,
    ).delete()
    db.flush()

    # Aggregate per topic_code in one query.
    rows = (
        db.query(
            BudgetLine.topic_code,
            func.count(BudgetLine.id).label("n_lines"),
            func.coalesce(func.sum(BudgetLine.amount), 0.0).label("amount_total"),
            func.coalesce(
                func.sum(case((BudgetLine.is_retro.is_(False), BudgetLine.amount), else_=0.0)),
                0.0,
            ).label("amount_regular"),
            func.coalesce(
                func.sum(case(
                    ((BudgetLine.is_retro.is_(True)) & (BudgetLine.amount > 0), BudgetLine.amount),
                    else_=0.0,
                )),
                0.0,
            ).label("amount_retro_pos"),
            func.coalesce(
                func.sum(case(
                    ((BudgetLine.is_retro.is_(True)) & (BudgetLine.amount < 0), BudgetLine.amount),
                    else_=0.0,
                )),
                0.0,
            ).label("amount_retro_neg"),
            func.max(BudgetLine.budget_topic).label("topic_name"),
        )
        .filter(BudgetLine.run_id == run_id)
        .group_by(BudgetLine.topic_code)
        .all()
    )

    inserted = 0
    for r in rows:
        db.add(CodeHistory(
            municipality_id=muni_id,
            topic_code=str(r.topic_code),
            year_month=year_month,
            run_id=run_id,
            topic_name=(r.topic_name or "")[:255] if r.topic_name else None,
            amount_total=round(float(r.amount_total or 0.0), 2),
            amount_regular=round(float(r.amount_regular or 0.0), 2),
            amount_retro_pos=round(float(r.amount_retro_pos or 0.0), 2),
            amount_retro_neg=round(float(r.amount_retro_neg or 0.0), 2),
            line_count=int(r.n_lines or 0),
        ))
        inserted += 1
    db.flush()
    return {"rows_inserted": inserted, "year_month": year_month, "municipality_id": muni_id}


def backfill_all_runs_code_history(db: Session) -> Dict[str, Any]:
    runs = (
        db.query(MonthlyRun)
        .order_by(MonthlyRun.municipality_id, MonthlyRun.month)
        .all()
    )
    updated = 0
    failures = []
    for run in runs:
        try:
            recompute_code_history_for_run(db, run.id)
            updated += 1
        except Exception as exc:  # noqa: BLE001
            failures.append({"run_id": run.id, "error": str(exc)[:200]})
    db.commit()
    return {"updated": updated, "failures": failures}
