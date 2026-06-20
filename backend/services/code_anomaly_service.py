"""
Code anomaly service — Priority 4.

recompute_anomalies_for_run(db, run_id) — wipes and rebuilds the
CodeAnomaly rows for this run by reading topic_summaries (Priority 2)
populated immediately before us in upload.py. For each non-'normal'
TopicSummary row, emits one CodeAnomaly with a Hebrew narrative.
Also emits 'tie_out_gap' anomalies where tie_out_diff != 0.
Idempotent.
"""
from __future__ import annotations
from typing import Dict, Any
from sqlalchemy.orm import Session

from backend.models import MonthlyRun, TopicSummary, CodeAnomaly


def _narrative(flag_type: str, code: str, name: str, prev: float, curr: float, dpct: float, diff: float) -> str:
    name = (name or "")[:80]
    if flag_type == "new":
        return f"קוד {code} ({name}) חדש החודש — סכום ₪{abs(curr):,.0f}"
    if flag_type == "disappeared":
        return f"קוד {code} ({name}) נעלם החודש — קיבל ₪{abs(prev):,.0f} בחודש קודם"
    if flag_type == "outlier":
        sign = "+" if dpct >= 0 else ""
        return f"קוד {code} ({name}) השתנה ב-{sign}{dpct:.1f}%: מ-₪{prev:,.0f} ל-₪{curr:,.0f}"
    if flag_type == "tie_out_gap":
        return f"קוד {code}: פער של ₪{abs(diff):,.0f} בין החשבונית לפירוט"
    return f"קוד {code}: {flag_type}"


def recompute_anomalies_for_run(db: Session, run_id: int) -> Dict[str, Any]:
    run = db.query(MonthlyRun).filter(MonthlyRun.id == run_id).first()
    if run is None:
        raise ValueError(f"MonthlyRun id={run_id} not found")

    # Wipe & rebuild
    db.query(CodeAnomaly).filter(CodeAnomaly.run_id == run_id).delete()
    db.flush()

    summaries = db.query(TopicSummary).filter(TopicSummary.run_id == run_id).all()
    counts = {"new": 0, "outlier": 0, "disappeared": 0, "tie_out_gap": 0}

    for s in summaries:
        # Flag from topic_summary itself (new/outlier/disappeared)
        if s.anomaly_flag and s.anomaly_flag != "normal":
            ft = s.anomaly_flag
            narrative = _narrative(
                ft, s.topic_code, s.topic_name or "",
                float(s.prev_month_amount or 0.0),
                float(s.amount_total or 0.0),
                float(s.delta_pct or 0.0),
                float(s.tie_out_diff or 0.0),
            )
            db.add(CodeAnomaly(
                run_id=run_id,
                municipality_id=run.municipality_id,
                topic_code=s.topic_code,
                flag_type=ft,
                previous_value=s.prev_month_amount,
                current_value=s.amount_total,
                delta=s.delta_abs,
                delta_pct=s.delta_pct,
                narrative=narrative[:500],
            ))
            counts[ft] = counts.get(ft, 0) + 1

        # Independent 'tie_out_gap' anomaly when CHESHBONIT ≠ detail-sum
        if s.tie_out_diff and abs(float(s.tie_out_diff)) > 0.01:
            narrative = _narrative(
                "tie_out_gap", s.topic_code, s.topic_name or "",
                float(s.prev_month_amount or 0.0),
                float(s.amount_total or 0.0),
                float(s.delta_pct or 0.0),
                float(s.tie_out_diff),
            )
            db.add(CodeAnomaly(
                run_id=run_id,
                municipality_id=run.municipality_id,
                topic_code=s.topic_code,
                flag_type="tie_out_gap",
                previous_value=None,
                current_value=s.amount_total,
                delta=s.tie_out_diff,
                delta_pct=None,
                narrative=narrative[:500],
            ))
            counts["tie_out_gap"] = counts.get("tie_out_gap", 0) + 1

    db.flush()
    return {"run_id": run_id, "anomalies": counts, "total": sum(counts.values())}
