"""
Topic summary service — Priority 2.

recompute_topic_summaries_for_run(db, run_id) — wipes & rebuilds the
TopicSummary rows for one run from budget_lines + ingestion_warnings,
joining the previous run for MoM context. Idempotent.

backfill_all_runs_topic_summaries(db) — runs the above for every
monthly_runs.id in chronological order (so prev-month lookups work as
we go).

Anomaly rules:
  'new'     — no prev run OR prev_month_amount in (None, 0), and |amount_total| > 1
  'outlier' — has prev, |delta_pct| > 50
  'normal'  — otherwise

'disappeared' is NOT implemented yet (Priority 4 — requires phantom rows
for codes that existed in prior runs but vanished this month).
"""
from __future__ import annotations

from typing import Dict, Any, Optional

from sqlalchemy import func, distinct, case
from sqlalchemy.orm import Session

from backend.models import BudgetLine, MonthlyRun, TopicSummary
from backend.models.ingestion_warning import IngestionWarning


def _find_prev_run(db: Session, run: MonthlyRun) -> Optional[MonthlyRun]:
    """Latest monthly_run for the same municipality with month < this.month."""
    return (
        db.query(MonthlyRun)
        .filter(
            MonthlyRun.municipality_id == run.municipality_id,
            MonthlyRun.id != run.id,
            MonthlyRun.month < run.month,
        )
        .order_by(MonthlyRun.month.desc())
        .first()
    )


def _per_topic_aggregates(db: Session, run_id: int) -> Dict[str, Dict[str, Any]]:
    """Single query: per (topic_code) aggregates from budget_lines."""
    rows = (
        db.query(
            BudgetLine.topic_code,
            func.count(BudgetLine.id).label("n_lines"),
            func.coalesce(func.sum(BudgetLine.amount), 0.0).label("amount_total"),
            func.coalesce(
                func.sum(
                    case((BudgetLine.is_retro.is_(False), BudgetLine.amount), else_=0.0)
                ), 0.0
            ).label("amount_regular"),
            func.coalesce(
                func.sum(
                    case(
                        ((BudgetLine.is_retro.is_(True)) & (BudgetLine.amount > 0), BudgetLine.amount),
                        else_=0.0,
                    )
                ), 0.0
            ).label("amount_retro_pos"),
            func.coalesce(
                func.sum(
                    case(
                        ((BudgetLine.is_retro.is_(True)) & (BudgetLine.amount < 0), BudgetLine.amount),
                        else_=0.0,
                    )
                ), 0.0
            ).label("amount_retro_neg"),
            func.max(BudgetLine.budget_topic).label("topic_name"),
        )
        .filter(BudgetLine.run_id == run_id)
        .group_by(BudgetLine.topic_code)
        .all()
    )
    return {
        r.topic_code: {
            "n_lines": r.n_lines,
            "amount_total": float(r.amount_total or 0.0),
            "amount_regular": float(r.amount_regular or 0.0),
            "amount_retro_pos": float(r.amount_retro_pos or 0.0),
            "amount_retro_neg": float(r.amount_retro_neg or 0.0),
            "topic_name": r.topic_name,
        }
        for r in rows
    }


def _institutions_for_topic(db: Session, run_id: int, topic_code: str) -> Dict[str, Any]:
    """
    n_institutions (distinct institution_code) + top one by |amount|.
    Joins budget_lines -> budget_line_institutions for the per-school breakdown.
    Returns dict; top fields are None if no institution row exists for this topic.
    """
    from backend.models.budget_line_institution import BudgetLineInstitution
    rows = (
        db.query(
            BudgetLineInstitution.institution_code,
            BudgetLineInstitution.institution_name,
            func.sum(BudgetLineInstitution.amount).label("s"),
        )
        .join(BudgetLine, BudgetLine.id == BudgetLineInstitution.budget_line_id)
        .filter(
            BudgetLine.run_id == run_id,
            BudgetLine.topic_code == topic_code,
        )
        .group_by(BudgetLineInstitution.institution_code, BudgetLineInstitution.institution_name)
        .all()
    )
    if not rows:
        return {
            "n_institutions": 0,
            "top_institution_code": None,
            "top_institution_name": None,
            "top_institution_amount": None,
        }
    # Distinct institution_code count (collapse multiple rows with same code+name OR same code different name).
    distinct_codes = {str(r.institution_code) for r in rows}
    top = max(rows, key=lambda r: abs(float(r.s or 0.0)))
    return {
        "n_institutions": len(distinct_codes),
        "top_institution_code": str(top.institution_code) if top.institution_code else None,
        "top_institution_name": str(top.institution_name) if top.institution_name else None,
        "top_institution_amount": round(float(top.s or 0.0), 2),
    }


def _tie_out_diff(db: Session, run_id: int, topic_code: str) -> float:
    """Pull the parser's recorded tie-out gap for this (run, topic), else 0."""
    w = (
        db.query(IngestionWarning)
        .filter(
            IngestionWarning.run_id == run_id,
            IngestionWarning.topic_code == str(topic_code),
            IngestionWarning.category.in_(("tie_out_mismatch", "additive_closure_failed")),
        )
        .order_by(IngestionWarning.id.desc())
        .first()
    )
    if w and w.delta is not None:
        try:
            return float(w.delta)
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _prev_topic_amount(db: Session, prev_run_id: int, topic_code: str) -> Optional[float]:
    val = (
        db.query(func.coalesce(func.sum(BudgetLine.amount), 0.0))
        .filter(BudgetLine.run_id == prev_run_id, BudgetLine.topic_code == topic_code)
        .scalar()
    )
    if val is None:
        return None
    return round(float(val), 2)


def _classify(amount_total: float, prev: Optional[float], delta_pct: Optional[float]) -> str:
    if prev is None or prev == 0.0:
        return "new" if abs(amount_total) > 1.0 else "normal"
    if delta_pct is not None and abs(delta_pct) > 50.0:
        return "outlier"
    return "normal"


def recompute_topic_summaries_for_run(db: Session, run_id: int) -> Dict[str, Any]:
    run = db.query(MonthlyRun).filter(MonthlyRun.id == run_id).first()
    if run is None:
        raise ValueError(f"MonthlyRun id={run_id} not found")

    # Wipe & rebuild — idempotent.
    db.query(TopicSummary).filter(TopicSummary.run_id == run_id).delete()
    db.flush()

    aggs = _per_topic_aggregates(db, run_id)
    prev_run = _find_prev_run(db, run)
    prev_run_id = prev_run.id if prev_run else None

    flag_counts = {"new": 0, "outlier": 0, "normal": 0, "disappeared": 0}
    inserted = 0

    for topic_code, agg in aggs.items():
        topic_code_str = str(topic_code)
        amount_total = round(agg["amount_total"], 2)

        prev_amount = _prev_topic_amount(db, prev_run_id, topic_code_str) if prev_run_id else None
        delta_abs = None
        delta_pct = None
        if prev_amount is not None:
            delta_abs = round(amount_total - prev_amount, 2)
            if prev_amount != 0:
                delta_pct = round(delta_abs / abs(prev_amount) * 100.0, 2)

        flag = _classify(amount_total, prev_amount, delta_pct)
        flag_counts[flag] = flag_counts.get(flag, 0) + 1

        inst = _institutions_for_topic(db, run_id, topic_code_str)
        diff = _tie_out_diff(db, run_id, topic_code_str)

        db.add(TopicSummary(
            run_id=run_id,
            municipality_id=run.municipality_id,
            topic_code=topic_code_str,
            topic_name=(agg["topic_name"] or "")[:255] if agg["topic_name"] else None,
            amount_total=amount_total,
            amount_regular=round(agg["amount_regular"], 2),
            amount_retro_pos=round(agg["amount_retro_pos"], 2),
            amount_retro_neg=round(agg["amount_retro_neg"], 2),
            prev_run_id=prev_run_id if prev_amount is not None else None,
            prev_month_amount=prev_amount,
            delta_abs=delta_abs,
            delta_pct=delta_pct,
            anomaly_flag=flag,
            tie_out_diff=round(diff, 2),
            n_institutions=inst["n_institutions"],
            top_institution_code=inst["top_institution_code"],
            top_institution_name=(inst["top_institution_name"] or None) if inst["top_institution_name"] else None,
            top_institution_amount=inst["top_institution_amount"],
        ))
        inserted += 1


    # Priority-4: phantom rows for codes that existed in prev_run but vanished.
    if prev_run_id is not None:
        from sqlalchemy import distinct as _distinct
        current_codes = {str(c) for c in aggs.keys()}
        prev_code_rows = (
            db.query(_distinct(BudgetLine.topic_code))
            .filter(BudgetLine.run_id == prev_run_id)
            .all()
        )
        prev_codes = {str(r[0]) for r in prev_code_rows}
        for code in (prev_codes - current_codes):
            prev_amt = _prev_topic_amount(db, prev_run_id, code)
            if prev_amt is None or abs(prev_amt) < 1.0:
                continue
            # Pull a topic name from prev run for display purposes.
            name_row = (
                db.query(BudgetLine.budget_topic)
                .filter(BudgetLine.run_id == prev_run_id, BudgetLine.topic_code == code)
                .first()
            )
            topic_name = (name_row[0] if name_row else None) or None
            db.add(TopicSummary(
                run_id=run_id,
                municipality_id=run.municipality_id,
                topic_code=code,
                topic_name=(topic_name or "")[:255] if topic_name else None,
                amount_total=0.0,
                amount_regular=0.0,
                amount_retro_pos=0.0,
                amount_retro_neg=0.0,
                prev_run_id=prev_run_id,
                prev_month_amount=prev_amt,
                delta_abs=-prev_amt,
                delta_pct=-100.0,
                anomaly_flag="disappeared",
                tie_out_diff=0.0,
                n_institutions=0,
                top_institution_code=None,
                top_institution_name=None,
                top_institution_amount=None,
            ))
            flag_counts["disappeared"] = flag_counts.get("disappeared", 0) + 1
            inserted += 1

    db.flush()
    return {
        "topics": inserted,
        "anomalies": flag_counts,
        "prev_run_id": prev_run_id,
    }


def backfill_all_runs_topic_summaries(db: Session) -> Dict[str, Any]:
    runs = (
        db.query(MonthlyRun)
        .order_by(MonthlyRun.municipality_id, MonthlyRun.month)
        .all()
    )
    updated = 0
    failures = []
    for run in runs:
        try:
            recompute_topic_summaries_for_run(db, run.id)
            updated += 1
        except Exception as exc:  # noqa: BLE001
            failures.append({"run_id": run.id, "error": str(exc)[:200]})
    db.commit()
    return {"updated": updated, "failures": failures}
