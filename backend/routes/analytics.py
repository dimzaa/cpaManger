"""
Analytics & Trends Routes (ניתוח ומגמות)

GET /api/analytics/trends/{municipality_id}        — Multi-month trends per code
GET /api/analytics/year-comparison/{municipality_id}/{month} — YoY comparison
GET /api/analytics/forecast/{municipality_id}      — Next-month prediction
GET /api/analytics/anomalies/{municipality_id}/{month} — Anomaly detection
GET /api/analytics/retro-aging/{municipality_id}/{month}  — Retro payment aging
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.models.budget_line import BudgetLine
from backend.models.monthly_run import MonthlyRun
from backend.models.municipality import Municipality
from backend.models.user import User
from backend.models.approved_explanation import ApprovedExplanation
from backend.models.class_enrollment import ClassEnrollment
from backend.models.staff_positions import StaffPosition
from backend.models.transport_route import TransportRoute
from backend.utils.auth_guards import require_login
from backend.routes.positions import CHILD_RATE

try:
    from backend.data.purple_booklet_rules import BUDGET_TOPIC_RULES
except Exception:
    BUDGET_TOPIC_RULES = {}

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# ──────────────────────────────────────────────────────────
# Code metadata
# ──────────────────────────────────────────────────────────
CODE_META = {
    "3":   {"name": "גני ילדים",      "color": "#10B981"},
    "19":  {"name": "עוזרות",         "color": "#F59E0B"},
    "33":  {"name": "גננות מדינה",    "color": "#EF4444"},
    "5":   {"name": "קב\"ס",          "color": "#8B5CF6"},
    "45":  {"name": "קב\"ס",          "color": "#8B5CF6"},
    "52":  {"name": "הסעות חינוך רגיל",  "color": "#0EA5E9"},
    "140": {"name": "הסעות חינוך מיוחד", "color": "#6366F1"},
}

HEBREW_MONTHS = {
    "01": "ינואר", "02": "פברואר", "03": "מרץ",
    "04": "אפריל", "05": "מאי",    "06": "יוני",
    "07": "יולי",  "08": "אוגוסט", "09": "ספטמבר",
    "10": "אוקטובר","11": "נובמבר","12": "דצמבר",
}

PRIMARY_CODES = ["3", "19", "33"]


def _month_display(month_str: str) -> str:
    """Convert YYYY-MM to Hebrew month name + year."""
    if not month_str or len(month_str) < 7:
        return month_str
    year, mon = month_str[:4], month_str[5:7]
    return f"{HEBREW_MONTHS.get(mon, mon)} {year}"


def _months_between(older: str, newer: str) -> int:
    """Return number of months between two YYYY-MM strings."""
    try:
        o = datetime.strptime(older, "%Y-%m")
        n = datetime.strptime(newer, "%Y-%m")
        return (n.year - o.year) * 12 + (n.month - o.month)
    except Exception:
        return 0


def _estimate_children(amount: float) -> int:
    """Rough estimate of children from code-3 amount."""
    if not amount or amount <= 0:
        return 0
    return max(0, round(amount / CHILD_RATE["normal"]))


def _parse_month(month: str) -> tuple[str, int]:
    """Validate YYYY-MM and return (month_str, year_int)."""
    try:
        parsed = datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise HTTPException(status_code=400, detail="פורמט חודש לא תקין — השתמש ב-YYYY-MM")
    return month, parsed.year


def _get_run_for_month(db: Session, municipality_id: int, month: str) -> Optional[MonthlyRun]:
    """
    Match detail-page semantics: choose one monthly run for municipality+month.
    We also enforce year to avoid any accidental cross-year collisions.
    """
    month_str, year = _parse_month(month)
    return (
        db.query(MonthlyRun)
        .filter(
            MonthlyRun.municipality_id == municipality_id,
            MonthlyRun.month == month_str,
            MonthlyRun.year == year,
        )
        .first()
    )


def _is_real_line(line) -> bool:
    """
    Filter out placeholder/garbage lines that pollute aggregations.

    The ingester sometimes keeps blank rows from the source file
    (amount=0, topic_code missing or '0', no topic name). These
    inflate counts, add phantom 'קוד 0' rows in tables, and break
    retro-share math. This helper is the single source of truth for
    "is this an actual budget line?".
    """
    code = (line.topic_code or '').strip()
    if not code or code == '0':
        # A code of '0' with no topic text and zero amount is garbage.
        if float(line.amount or 0) == 0 and not (line.budget_topic or '').strip():
            return False
    return True


def _safe_retro_share(retro: float, regular: float) -> float:
    """
    Percentage of activity that is retro — expressed over the sum of
    absolute movements, not the signed total. Avoids >100% or <0%
    artefacts when regular and retro have opposite signs (legitimate
    for deduction codes such as 33).
    """
    denom = abs(retro) + abs(regular)
    if denom <= 0.01:
        return 0.0
    return round((abs(retro) / denom) * 100, 1)


def _get_run_lines(db: Session, run_id: int) -> List[BudgetLine]:
    """
    Return all lines for a run, excluding blank/garbage rows that
    inflate counts without representing real budget activity.
    """
    rows = (
        db.query(BudgetLine)
        .filter(BudgetLine.run_id == run_id)
        .all()
    )
    return [r for r in rows if _is_real_line(r)]


def _check_access(current_user: User, municipality_id: int):
    if current_user.role == "municipality":
        if current_user.municipality_id != municipality_id:
            raise HTTPException(status_code=403, detail="אין הרשאה לצפות בנתוני רשות אחרת")


def _get_municipality(db: Session, municipality_id: int) -> Municipality:
    m = db.query(Municipality).filter(Municipality.id == municipality_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="הרשות המקומית לא נמצאה")
    return m


# ──────────────────────────────────────────────────────────
# ENDPOINT 1 — Trends
# ──────────────────────────────────────────────────────────

@router.get("/trends/{municipality_id}")
async def get_trends(
    municipality_id: int,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """
    Returns multi-month budget trends for all codes,
    ordered chronologically.
    """
    _check_access(current_user, municipality_id)
    muni = _get_municipality(db, municipality_id)

    # Get all distinct current_months that have data for this municipality
    months_q = (
        db.query(BudgetLine.current_month)
        .filter(BudgetLine.municipality_id == municipality_id)
        .distinct()
        .order_by(BudgetLine.current_month)
        .all()
    )
    months = [r[0] for r in months_q]

    if not months:
        return {
            "municipality_id": municipality_id,
            "municipality_name": muni.name,
            "months_available": [],
            "trends": {},
            "total_budget_trend": [],
        }

    # Build trends per code
    trends: Dict[str, Any] = {}
    total_by_month: Dict[str, float] = {m: 0.0 for m in months}

    all_lines = (
        db.query(BudgetLine)
        .filter(BudgetLine.municipality_id == municipality_id)
        .all()
    )

    # Group lines by current_month × topic_code
    grouped: Dict[str, Dict[str, List[BudgetLine]]] = {}
    for line in all_lines:
        grouped.setdefault(line.current_month, {}).setdefault(
            line.topic_code, []
        ).append(line)
        total_by_month[line.current_month] = (
            total_by_month.get(line.current_month, 0) + line.amount
        )

    # For each code that appears in any month
    all_codes = set()
    for month_data in grouped.values():
        all_codes.update(month_data.keys())

    for code in sorted(all_codes):
        meta = CODE_META.get(code, {"name": f"קוד {code}", "color": "#6B7280"})
        data_points = []

        for month in months:
            lines = grouped.get(month, {}).get(code, [])
            total = sum(l.amount for l in lines)
            retro_total = sum(l.amount for l in lines if l.is_retro)
            regular_total = total - retro_total
            items_count = len(lines)

            # Use actual children count from file if available, otherwise estimate
            children_count = 0
            if code == "3":
                actual = next((l.num_children for l in lines if l.num_children is not None), None)
                children_count = actual if actual is not None else _estimate_children(abs(regular_total))

            cost_per_child = 0.0
            if code == "3" and children_count > 0:
                cost_per_child = round(regular_total / children_count, 2)

            data_points.append({
                "month": month,
                "month_display": _month_display(month),
                "total": round(total, 2),
                "items_count": items_count,
                "children_count": children_count,
                "cost_per_child": cost_per_child,
                "retro_total": round(retro_total, 2),
                "regular_total": round(regular_total, 2),
            })

        # Calculate summary stats
        amounts = [d["total"] for d in data_points]
        first, last = amounts[0], amounts[-1]
        change_abs = round(last - first, 2)
        change_pct = round((change_abs / abs(first)) * 100, 1) if first != 0 else 0
        trend_dir = "up" if change_abs > 0 else ("down" if change_abs < 0 else "stable")
        avg = round(sum(amounts) / len(amounts), 2) if amounts else 0

        trends[code] = {
            "name": meta["name"],
            "color": meta["color"],
            "data": data_points,
            "change_absolute": change_abs,
            "change_percent": change_pct,
            "trend_direction": trend_dir,
            "average": avg,
            "min": min(amounts) if amounts else 0,
            "max": max(amounts) if amounts else 0,
        }

    total_trend = [
        {"month": m, "month_display": _month_display(m), "total": round(total_by_month[m], 2)}
        for m in months
    ]

    return {
        "municipality_id": municipality_id,
        "municipality_name": muni.name,
        "months_available": months,
        "trends": trends,
        "total_budget_trend": total_trend,
    }


# ──────────────────────────────────────────────────────────
# ENDPOINT 2 — Year Comparison
# ──────────────────────────────────────────────────────────

@router.get("/year-comparison/{municipality_id}/{month}")
async def get_year_comparison(
    municipality_id: int,
    month: str,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    _check_access(current_user, municipality_id)
    muni = _get_municipality(db, municipality_id)

    # Previous year same month
    try:
        curr_date = datetime.strptime(month, "%Y-%m")
        prev_date = curr_date.replace(year=curr_date.year - 1)
        prev_month = prev_date.strftime("%Y-%m")
    except ValueError:
        raise HTTPException(status_code=400, detail="פורמט חודש לא תקין — השתמש ב-YYYY-MM")

    def _month_data(m: str):
        lines = (
            db.query(BudgetLine)
            .filter(
                BudgetLine.municipality_id == municipality_id,
                BudgetLine.current_month == m,
            )
            .all()
        )
        if not lines:
            return None
        by_code: Dict[str, float] = {}
        for l in lines:
            by_code[l.topic_code] = by_code.get(l.topic_code, 0) + l.amount
        return {
            "month": m,
            "month_display": _month_display(m),
            "total": round(sum(l.amount for l in lines), 2),
            "by_code": {
                code: {
                    "amount": round(amt, 2),
                    "name": CODE_META.get(code, {}).get("name", f"קוד {code}"),
                }
                for code, amt in by_code.items()
            },
            "items_count": len(lines),
        }

    current_data = _month_data(month)
    previous_data = _month_data(prev_month)

    return {
        "current_month": month,
        "current_month_display": _month_display(month),
        "comparison_month": prev_month,
        "comparison_month_display": _month_display(prev_month),
        "has_previous_year": previous_data is not None,
        "current_data": current_data,
        "previous_data": previous_data,
        "message": None if previous_data else f"אין נתונים לחודש {_month_display(prev_month)}",
    }


# ──────────────────────────────────────────────────────────
# ENDPOINT 3 — Forecast
# ──────────────────────────────────────────────────────────

@router.get("/forecast/{municipality_id}")
async def get_forecast(
    municipality_id: int,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    _check_access(current_user, municipality_id)
    muni = _get_municipality(db, municipality_id)

    # Get last 6 months of totals per current_month
    months_q = (
        db.query(BudgetLine.current_month, func.sum(BudgetLine.amount).label("total"))
        .filter(BudgetLine.municipality_id == municipality_id)
        .group_by(BudgetLine.current_month)
        .order_by(BudgetLine.current_month)
        .all()
    )
    rows = [(r[0], float(r[1])) for r in months_q]

    if not rows:
        return {
            "forecast_month": None,
            "forecast_month_display": None,
            "predicted_total": None,
            "confidence": "none",
            "confidence_reason": "אין נתונים זמינים",
            "based_on_months": [],
            "change_from_last": None,
            "change_percent": None,
            "by_code": {},
            "disclaimer": "לא ניתן לחשב תחזית ללא נתונים",
        }

    # Keep only last 6
    rows = rows[-6:]
    month_strs = [r[0] for r in rows]
    totals = [r[1] for r in rows]

    # Next month
    try:
        last_date = datetime.strptime(rows[-1][0], "%Y-%m")
        next_date = last_date + relativedelta(months=1)
        forecast_month = next_date.strftime("%Y-%m")
    except Exception:
        forecast_month = "unknown"

    n = len(rows)
    if n == 1:
        predicted = totals[0]
        confidence = "low"
        confidence_reason = "רק חודש נתונים אחד זמין — בלתי אפשרי לחשב מגמה"
    elif n == 2:
        delta = totals[-1] - totals[-2]
        predicted = totals[-1] + delta
        confidence = "low"
        confidence_reason = "רק 2 חודשים של נתונים זמינים — דיוק נמוך"
    else:
        # Weighted average of differences, more weight to recent
        deltas = [totals[i] - totals[i-1] for i in range(1, n)]
        weights = list(range(1, len(deltas) + 1))
        weighted_delta = sum(d * w for d, w in zip(deltas, weights)) / sum(weights)
        predicted = totals[-1] + weighted_delta
        confidence = "medium" if n < 5 else "high"
        confidence_reason = (
            f"מבוסס על {n} חודשים — דיוק סביר" if n < 5
            else f"מבוסס על {n} חודשים — דיוק טוב"
        )

    predicted = round(predicted, 2)
    change_from_last = round(predicted - totals[-1], 2)
    change_pct = round((change_from_last / abs(totals[-1])) * 100, 1) if totals[-1] != 0 else 0

    # Per-code forecast
    by_code_q = (
        db.query(BudgetLine.topic_code, BudgetLine.current_month, func.sum(BudgetLine.amount).label("total"))
        .filter(BudgetLine.municipality_id == municipality_id)
        .group_by(BudgetLine.topic_code, BudgetLine.current_month)
        .order_by(BudgetLine.current_month)
        .all()
    )
    # Group by code
    code_rows: Dict[str, List] = {}
    for r in by_code_q:
        code_rows.setdefault(r[0], []).append((r[1], float(r[2])))

    by_code_forecast: Dict[str, Any] = {}
    for code, code_data in code_rows.items():
        code_data = sorted(code_data)[-6:]
        code_totals = [d[1] for d in code_data]
        if len(code_totals) == 1:
            code_pred = code_totals[-1]
            code_trend = "stable"
        elif len(code_totals) == 2:
            delta = code_totals[-1] - code_totals[-2]
            code_pred = code_totals[-1] + delta
            code_trend = "up" if delta > 0 else ("down" if delta < 0 else "stable")
        else:
            code_deltas = [code_totals[i] - code_totals[i-1] for i in range(1, len(code_totals))]
            code_weights = list(range(1, len(code_deltas) + 1))
            w_delta = sum(d * w for d, w in zip(code_deltas, code_weights)) / sum(code_weights)
            code_pred = code_totals[-1] + w_delta
            code_trend = "up" if w_delta > 0 else ("down" if w_delta < 0 else "stable")

        by_code_forecast[code] = {
            "name": CODE_META.get(code, {}).get("name", f"קוד {code}"),
            "predicted": round(code_pred, 2),
            "trend": code_trend,
            "last_actual": code_totals[-1],
        }

    return {
        "forecast_month": forecast_month,
        "forecast_month_display": _month_display(forecast_month),
        "predicted_total": predicted,
        "confidence": confidence,
        "confidence_reason": confidence_reason,
        "based_on_months": month_strs,
        "based_on_totals": [round(t, 2) for t in totals],
        "change_from_last": change_from_last,
        "change_percent": change_pct,
        "by_code": by_code_forecast,
        "disclaimer": "* תחזית זו מבוססת על מגמות היסטוריות בלבד. גורמים כמו שינויי מדיניות, עדכוני שכר או שינויים ברישום ילדים עשויים להשפיע על הסכום בפועל.",
    }


# ──────────────────────────────────────────────────────────
# ENDPOINT 4 — Anomaly Detection
# ──────────────────────────────────────────────────────────

@router.get("/anomalies/{municipality_id}/{month}")
async def get_anomalies(
    municipality_id: int,
    month: str,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    _check_access(current_user, municipality_id)
    _get_municipality(db, municipality_id)

    # Find previous month
    try:
        curr_date = datetime.strptime(month, "%Y-%m")
        prev_date = curr_date - relativedelta(months=1)
        prev_month = prev_date.strftime("%Y-%m")
    except ValueError:
        raise HTTPException(status_code=400, detail="פורמט חודש לא תקין")

    current_lines = (
        db.query(BudgetLine)
        .filter(
            BudgetLine.municipality_id == municipality_id,
            BudgetLine.current_month == month,
        )
        .all()
    )
    prev_lines = (
        db.query(BudgetLine)
        .filter(
            BudgetLine.municipality_id == municipality_id,
            BudgetLine.current_month == prev_month,
        )
        .all()
    )

    # Group totals by code
    def _group_by_code(lines):
        result = {}
        for l in lines:
            result[l.topic_code] = result.get(l.topic_code, 0) + l.amount
        return result

    curr_by_code = _group_by_code(current_lines)
    prev_by_code = _group_by_code(prev_lines)

    anomalies = []
    anomaly_id = 0

    def _add(anomaly_type, severity, title, description, recommendation, extra=None):
        nonlocal anomaly_id
        anomaly_id += 1
        a = {
            "id": f"{anomaly_type}_{anomaly_id}",
            "type": anomaly_type,
            "severity": severity,
            "title": title,
            "description": description,
            "recommendation": recommendation,
        }
        if extra:
            a.update(extra)
        anomalies.append(a)

    # 1. LARGE JUMP
    for code, curr_amt in curr_by_code.items():
        prev_amt = prev_by_code.get(code)
        if prev_amt is None or prev_amt == 0:
            continue
        change_pct = ((curr_amt - prev_amt) / abs(prev_amt)) * 100
        if change_pct > 100:
            _add(
                "large_jump", "high",
                "קפיצה גדולה מאוד בתשלום",
                f"קוד {code} עלה ב-{change_pct:.0f}% מ-{_month_display(prev_month)} ל-{_month_display(month)}",
                "בדוק עם משרד החינוך אם יש תשלום רטרו גדול שמצדיק זאת",
                {"budget_code": code, "previous_amount": round(prev_amt), "current_amount": round(curr_amt), "change_percent": round(change_pct, 1)},
            )
        elif change_pct > 50:
            _add(
                "large_jump", "medium",
                "קפיצה גדולה בתשלום",
                f"קוד {code} עלה ב-{change_pct:.0f}% מ-{_month_display(prev_month)} ל-{_month_display(month)}",
                "בדוק אם מספר הילדים השתנה או אם יש תשלומי רטרו",
                {"budget_code": code, "previous_amount": round(prev_amt), "current_amount": round(curr_amt), "change_percent": round(change_pct, 1)},
            )

    # 2. SUDDEN DROP
    for code, prev_amt in prev_by_code.items():
        curr_amt = curr_by_code.get(code, 0)
        if prev_amt == 0:
            continue
        drop_pct = ((prev_amt - curr_amt) / abs(prev_amt)) * 100
        if drop_pct > 50:
            _add(
                "sudden_drop", "high",
                "ירידה חדה בתשלום",
                f"קוד {code} ירד ב-{drop_pct:.0f}% מ-{_month_display(prev_month)} ל-{_month_display(month)}",
                "בדוק אם ילדים יצאו מהמערכת או אם יש טעות בהעלאת הקובץ",
                {"budget_code": code, "previous_amount": round(prev_amt), "current_amount": round(curr_amt), "drop_percent": round(drop_pct, 1)},
            )
        elif drop_pct > 30:
            _add(
                "sudden_drop", "medium",
                "ירידה גדולה בתשלום",
                f"קוד {code} ירד ב-{drop_pct:.0f}% מ-{_month_display(prev_month)} ל-{_month_display(month)}",
                "בדוק שינויים ברישום ילדים או עדכוני שכר",
                {"budget_code": code, "previous_amount": round(prev_amt), "current_amount": round(curr_amt), "drop_percent": round(drop_pct, 1)},
            )

    # 3. RETRO TOO OLD
    for line in current_lines:
        if not line.is_retro or not line.period_month:
            continue
        months_old = _months_between(line.period_month, month)
        if months_old >= 7:
            _add(
                "retro_too_old", "medium",
                "תשלום רטרו ישן מאוד",
                f"תשלום עבור {_month_display(line.period_month)} — {months_old} חודשים אחורה",
                "בדוק עם משרד החינוך מדוע התשלום התעכב כל כך",
                {
                    "budget_code": line.topic_code,
                    "amount": round(line.amount, 2),
                    "period_month": line.period_month,
                    "current_month": month,
                    "months_old": months_old,
                },
            )
        elif months_old >= 4:
            _add(
                "retro_too_old", "low",
                "תשלום רטרו ישן",
                f"תשלום עבור {_month_display(line.period_month)} — {months_old} חודשים אחורה",
                "מומלץ לבדוק אם התשלום צפוי או מאוחר",
                {
                    "budget_code": line.topic_code,
                    "amount": round(line.amount, 2),
                    "period_month": line.period_month,
                    "current_month": month,
                    "months_old": months_old,
                },
            )

    # 4. MISSING PAYMENT
    for code in prev_by_code:
        if code not in curr_by_code:
            _add(
                "missing_payment", "high",
                "תשלום חסר",
                f"קוד {code} הופיע בחודש הקודם אך חסר לחלוטין ב-{_month_display(month)}",
                "בדוק אם הקובץ הועלה כראוי ואם לא נשכחה שורה",
                {"budget_code": code},
            )

    # 5. DUPLICATE AMOUNTS
    seen_amounts: Dict[str, Dict[float, int]] = {}
    for line in current_lines:
        key = f"{line.topic_code}|{line.period_month}"
        seen_amounts.setdefault(key, {})
        seen_amounts[key][line.amount] = seen_amounts[key].get(line.amount, 0) + 1
    for key, amounts in seen_amounts.items():
        for amt, cnt in amounts.items():
            if cnt > 1 and abs(amt) > 1000:
                code = key.split("|")[0]
                _add(
                    "duplicate_amounts", "medium",
                    "כפילות בסכומים",
                    f"הסכום ₪{abs(round(amt)):,.0f} מופיע {cnt} פעמים עבור קוד {code}",
                    "בדוק אם הקובץ הועלה פעמיים או אם יש שורות כפולות",
                    {"budget_code": code, "amount": round(amt), "count": cnt},
                )
                break  # one anomaly per key

    # 6. COST PER CHILD SPIKE (code 3 only)
    curr_code3 = [l for l in current_lines if l.topic_code == "3" and not l.is_retro]
    prev_code3 = [l for l in prev_lines if l.topic_code == "3" and not l.is_retro]
    if curr_code3 and prev_code3:
        curr_total3 = sum(l.amount for l in curr_code3)
        prev_total3 = sum(l.amount for l in prev_code3)
        curr_actual = next((l.num_children for l in curr_code3 if l.num_children is not None), None)
        prev_actual = next((l.num_children for l in prev_code3 if l.num_children is not None), None)
        curr_children = curr_actual if curr_actual is not None else _estimate_children(curr_total3)
        prev_children = prev_actual if prev_actual is not None else _estimate_children(prev_total3)
        if curr_children > 0 and prev_children > 0:
            curr_cpc = curr_total3 / curr_children
            prev_cpc = prev_total3 / prev_children
            if prev_cpc != 0:
                cpc_change = ((curr_cpc - prev_cpc) / abs(prev_cpc)) * 100
                if abs(cpc_change) > 10:
                    _add(
                        "cost_per_child_spike", "low",
                        "שינוי בעלות לילד",
                        f"עלות לילד השתנתה ב-{cpc_change:.1f}% — ייתכן עדכון שכר",
                        "בדוק אם משרד החינוך עדכן את טבלאות השכר",
                        {"budget_code": "3", "previous_cpc": round(prev_cpc, 2), "current_cpc": round(curr_cpc, 2), "change_percent": round(cpc_change, 1)},
                    )

    sev_counts = {"high": 0, "medium": 0, "low": 0}
    for a in anomalies:
        sev_counts[a["severity"]] = sev_counts.get(a["severity"], 0) + 1

    return {
        "month": month,
        "month_display": _month_display(month),
        "anomalies": anomalies,
        "total_anomalies": len(anomalies),
        "high_severity": sev_counts["high"],
        "medium_severity": sev_counts["medium"],
        "low_severity": sev_counts["low"],
    }


# ──────────────────────────────────────────────────────────
# ENDPOINT 5 — Retro Aging
# ──────────────────────────────────────────────────────────

@router.get("/retro-aging/{municipality_id}/{month}")
async def get_retro_aging(
    municipality_id: int,
    month: str,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    _check_access(current_user, municipality_id)
    _get_municipality(db, municipality_id)

    retro_lines = (
        db.query(BudgetLine)
        .filter(
            BudgetLine.municipality_id == municipality_id,
            BudgetLine.current_month == month,
            BudgetLine.is_retro == True,
        )
        .order_by(BudgetLine.period_month)
        .all()
    )

    if not retro_lines:
        return {
            "total_retro_amount": 0,
            "retro_lines": [],
            "aging_summary": {
                "normal_0_3": {"count": 0, "amount": 0},
                "old_4_6": {"count": 0, "amount": 0},
                "very_old_7_plus": {"count": 0, "amount": 0},
            },
        }

    def _age_category(months_old: int):
        if months_old <= 3:
            return "רגיל", "green"
        elif months_old <= 6:
            return "ישן", "amber"
        else:
            return "ישן מאוד", "red"

    result_lines = []
    aging = {"normal_0_3": {"count": 0, "amount": 0.0}, "old_4_6": {"count": 0, "amount": 0.0}, "very_old_7_plus": {"count": 0, "amount": 0.0}}

    for line in retro_lines:
        months_old = _months_between(line.period_month or month, month)
        cat_label, cat_color = _age_category(months_old)

        if months_old <= 3:
            bucket = "normal_0_3"
        elif months_old <= 6:
            bucket = "old_4_6"
        else:
            bucket = "very_old_7_plus"

        aging[bucket]["count"] += 1
        aging[bucket]["amount"] += line.amount

        warning = None
        if months_old >= 7:
            warning = f"תשלום זה מחכה {months_old} חודשים — בדוק עם משרד החינוך"
        elif months_old >= 4:
            warning = f"תשלום מעט ישן — {months_old} חודשים"

        result_lines.append({
            "id": line.id,
            "topic": line.budget_topic,
            "code": line.topic_code,
            "period_month": line.period_month,
            "period_display": _month_display(line.period_month or ""),
            "current_month": month,
            "months_old": months_old,
            "amount": round(line.amount, 2),
            "age_category": cat_label,
            "age_color": cat_color,
            "warning": warning,
        })

    # Round aging amounts
    for k in aging:
        aging[k]["amount"] = round(aging[k]["amount"], 2)

    # Sort: oldest first
    result_lines.sort(key=lambda x: x["months_old"], reverse=True)

    return {
        "total_retro_amount": round(sum(l.amount for l in retro_lines), 2),
        "retro_lines": result_lines,
        "aging_summary": aging,
    }


# ──────────────────────────────────────────────────────────
# ENDPOINT 6 — All municipalities overview (admin only)
# ──────────────────────────────────────────────────────────

@router.get("/overview/{month}")
async def get_admin_overview(
    month: str,
    include_test: bool = False,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Admin-only: summary of all municipalities for a given month."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="גישה לאדמין בלבד")

    month_str, _ = _parse_month(month)

    municipalities_query = db.query(Municipality)
    if not include_test:
        municipalities_query = municipalities_query.filter(Municipality.is_test == False)
    municipalities = municipalities_query.all()
    result = []

    for muni in municipalities:
        run = _get_run_for_month(db, muni.id, month_str)
        if not run:
            result.append({
                "municipality_id": muni.id,
                "municipality_name": muni.name,
                "total": 0,
                "due_amount": 0,
                "paid_amount": 0,
                "gap_amount": 0,
                "has_data": False,
                "by_code": {},
            })
            continue

        lines = _get_run_lines(db, run.id)

        # Keep "total" as the exact sum of all code amounts for this selected month/run.
        by_code = {}
        for l in lines:
            by_code[l.topic_code] = round(by_code.get(l.topic_code, 0) + l.amount, 2)

        total = round(sum(by_code.values()), 2)

        # Keep due/paid aligned with detail-page normalization logic.
        raw_breakdown_total = float(run.breakdown_total) if run.breakdown_total is not None else 0.0
        raw_invoice_total = float(run.invoice_total) if run.invoice_total is not None else 0.0
        due_is_breakdown = abs(total - raw_breakdown_total) <= abs(total - raw_invoice_total)
        due_amount = raw_breakdown_total if due_is_breakdown else raw_invoice_total
        paid_amount = raw_invoice_total if due_is_breakdown else raw_breakdown_total
        gap_amount = round(due_amount - paid_amount, 2)

        result.append({
            "municipality_id": muni.id,
            "municipality_name": muni.name,
            "total": total,
            "due_amount": round(due_amount, 2),
            "paid_amount": round(paid_amount, 2),
            "gap_amount": gap_amount,
            "has_data": bool(lines),
            "by_code": by_code,
        })

    result.sort(key=lambda r: -r["total"])
    return {
        "month": month_str,
        "month_display": _month_display(month_str),
        "municipalities": result,
    }


# ──────────────────────────────────────────────────────────
# ENDPOINT 7 — YTD Cumulative
# ──────────────────────────────────────────────────────────

def _ytd_window(month: str, fiscal_start_month: int = 1) -> tuple[str, str]:
    """
    Return (start_month, end_month) as YYYY-MM inclusive for the YTD window.

    fiscal_start_month=1  → calendar year (Jan..month)
    fiscal_start_month=9  → Israeli educational year (Sep prev-year..month)
    """
    month_str, year = _parse_month(month)
    curr = datetime.strptime(month_str, "%Y-%m")
    if curr.month >= fiscal_start_month:
        start = curr.replace(month=fiscal_start_month, day=1)
    else:
        start = curr.replace(year=curr.year - 1, month=fiscal_start_month, day=1)
    return start.strftime("%Y-%m"), month_str


@router.get("/ytd/{municipality_id}/{month}")
async def get_ytd_cumulative(
    municipality_id: int,
    month: str,
    fiscal_start_month: int = 1,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """
    Year-to-date cumulative totals per topic since fiscal-year start.

    Returns per-topic cumulative ₪, months_covered count, avg_per_month,
    plus overall total and retro split — so the CPA can say
    "since Jan, Natzrat has received ₪X under code 3".
    """
    _check_access(current_user, municipality_id)
    muni = _get_municipality(db, municipality_id)

    if fiscal_start_month < 1 or fiscal_start_month > 12:
        raise HTTPException(status_code=400, detail="fiscal_start_month חייב להיות בין 1 ל-12")

    start_month, end_month = _ytd_window(month, fiscal_start_month)

    # Pull every line in the YTD window for this muni
    raw_lines = (
        db.query(BudgetLine)
        .filter(
            BudgetLine.municipality_id == municipality_id,
            BudgetLine.current_month >= start_month,
            BudgetLine.current_month <= end_month,
        )
        .all()
    )
    lines = [l for l in raw_lines if _is_real_line(l)]

    months_seen: set[str] = set()
    by_code: Dict[str, Dict[str, Any]] = {}
    grand_total = 0.0
    grand_retro = 0.0

    for line in lines:
        months_seen.add(line.current_month)
        code = line.topic_code or "0"
        amt = float(line.amount or 0.0)
        bucket = by_code.setdefault(code, {
            "topic_code": code,
            "topic_name": CODE_META.get(code, {}).get("name", f"קוד {code}"),
            "ytd_total": 0.0,
            "ytd_regular": 0.0,
            "ytd_retro": 0.0,
            "lines_count": 0,
            "months_with_data": set(),
        })
        bucket["ytd_total"] += amt
        bucket["lines_count"] += 1
        bucket["months_with_data"].add(line.current_month)
        if line.is_retro:
            bucket["ytd_retro"] += amt
            grand_retro += amt
        else:
            bucket["ytd_regular"] += amt
        grand_total += amt

    months_covered = sorted(months_seen)
    n_months = len(months_covered)

    by_code_list = []
    for code, b in by_code.items():
        months_with_data = sorted(b.pop("months_with_data"))
        b["months_with_data"] = months_with_data
        b["avg_per_month"] = round(b["ytd_regular"] / len(months_with_data), 2) if months_with_data else 0.0
        b["ytd_total"] = round(b["ytd_total"], 2)
        b["ytd_regular"] = round(b["ytd_regular"], 2)
        b["ytd_retro"] = round(b["ytd_retro"], 2)
        b["retro_share_pct"] = _safe_retro_share(b["ytd_retro"], b["ytd_regular"])
        by_code_list.append(b)

    by_code_list.sort(key=lambda r: -abs(r["ytd_total"]))

    # ── Annual projection (ytd × 12 ÷ months_covered) ─────────────────────
    projected_annual = round(grand_total * (12 / n_months), 2) if n_months else 0.0
    pct_of_projected = (
        round((grand_total / projected_annual) * 100, 1)
        if projected_annual else 0.0
    )

    # ── Fiscal-year cumulative gap (Σ breakdown - Σ invoice across runs) ──
    runs_in_window = (
        db.query(MonthlyRun)
        .filter(
            MonthlyRun.municipality_id == municipality_id,
            MonthlyRun.month >= start_month,
            MonthlyRun.month <= end_month,
        )
        .all()
    )
    fy_due = round(sum(float(r.breakdown_total or 0.0) for r in runs_in_window), 2)
    fy_paid = round(sum(float(r.invoice_total or 0.0) for r in runs_in_window), 2)
    fy_gap = round(fy_due - fy_paid, 2)

    # ── Smart bullets (computed facts, not prose rewrites) ────────────────
    bullets: List[str] = []
    if by_code_list:
        top3 = by_code_list[:3]
        top3_sum = sum(r["ytd_total"] for r in top3)
        top3_share = (top3_sum / grand_total * 100) if grand_total else 0
        names = ", ".join(f"{r['topic_name']} (₪{r['ytd_total']:,.0f})" for r in top3)
        bullets.append(
            f"שלושת הנושאים הגדולים מצטברים ל-₪{top3_sum:,.0f} ({top3_share:.1f}% מהסך): {names}"
        )
    if grand_total:
        bullets.append(
            f"תשלומי רטרו מהווים {round((grand_retro / grand_total) * 100, 1)}% "
            f"מסך התקבולים (₪{grand_retro:,.0f})."
        )
    if n_months and projected_annual:
        bullets.append(
            f"על בסיס {n_months} חודשים — תחזית שנתית: ₪{projected_annual:,.0f} "
            f"(נצברו עד כה {pct_of_projected}%)."
        )
    if fy_gap:
        sign_word = "עודף" if fy_gap < 0 else "חוסר"
        bullets.append(
            f"פער מצטבר בין מגיע לשולם בשנה: ₪{abs(fy_gap):,.0f} ({sign_word})."
        )

    return {
        "municipality_id": municipality_id,
        "municipality_name": muni.name,
        "fiscal_start_month": fiscal_start_month,
        "start_month": start_month,
        "start_month_display": _month_display(start_month),
        "end_month": end_month,
        "end_month_display": _month_display(end_month),
        "months_covered": months_covered,
        "months_covered_count": n_months,
        "ytd_total": round(grand_total, 2),
        "ytd_regular": round(grand_total - grand_retro, 2),
        "ytd_retro": round(grand_retro, 2),
        "ytd_retro_share_pct": _safe_retro_share(grand_retro, grand_total - grand_retro),
        "avg_per_month": round(grand_total / n_months, 2) if n_months else 0.0,
        "projected_annual": projected_annual,
        "pct_of_projected_annual": pct_of_projected,
        "fiscal_year_due_total": fy_due,
        "fiscal_year_paid_total": fy_paid,
        "fiscal_year_cumulative_gap": fy_gap,
        "smart_bullets": bullets,
        "by_code": by_code_list,
    }


# ──────────────────────────────────────────────────────────
# ENDPOINT 8 — Variance Drivers (waterfall)
# ──────────────────────────────────────────────────────────

@router.get("/variance-drivers/{municipality_id}/{month}")
async def get_variance_drivers(
    municipality_id: int,
    month: str,
    limit: int = 10,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """
    Rank topic-code changes month-over-month by absolute ₪ impact.

    Designed as a waterfall: CPA sees "this month's ₪X delta = +₪A code 3
    +₪B code 19 −₪C code 33". Each row includes delta_abs, delta_pct,
    share_of_total_change and a direction.
    """
    _check_access(current_user, municipality_id)
    _get_municipality(db, municipality_id)

    month_str, _ = _parse_month(month)
    prev_month = (datetime.strptime(month_str, "%Y-%m") - relativedelta(months=1)).strftime("%Y-%m")

    def _sum_by_code(m: str) -> Dict[str, float]:
        rows = (
            db.query(BudgetLine.topic_code, func.sum(BudgetLine.amount).label("total"))
            .filter(
                BudgetLine.municipality_id == municipality_id,
                BudgetLine.current_month == m,
            )
            .group_by(BudgetLine.topic_code)
            .all()
        )
        return {r[0] or "0": float(r[1] or 0.0) for r in rows}

    curr_by_code = _sum_by_code(month_str)
    prev_by_code = _sum_by_code(prev_month)

    curr_total = sum(curr_by_code.values())
    prev_total = sum(prev_by_code.values())
    total_delta = curr_total - prev_total

    all_codes = set(curr_by_code) | set(prev_by_code)
    drivers: List[Dict[str, Any]] = []
    for code in all_codes:
        prev = prev_by_code.get(code, 0.0)
        curr = curr_by_code.get(code, 0.0)
        delta = curr - prev
        if abs(delta) < 0.01:
            continue
        delta_pct = (delta / abs(prev) * 100) if prev else None
        drivers.append({
            "topic_code": code,
            "topic_name": CODE_META.get(code, {}).get("name", f"קוד {code}"),
            "previous_amount": round(prev, 2),
            "current_amount": round(curr, 2),
            "delta_abs": round(delta, 2),
            "delta_pct": round(delta_pct, 1) if delta_pct is not None else None,
            "direction": "up" if delta > 0 else "down",
            "share_of_total_change_pct": (
                round((delta / total_delta) * 100, 1) if abs(total_delta) > 0.01 else None
            ),
            "is_new_code": prev == 0 and curr != 0,
            "is_disappeared_code": curr == 0 and prev != 0,
        })

    drivers.sort(key=lambda r: -abs(r["delta_abs"]))
    top_drivers = drivers[: max(1, limit)]

    # Sanity: sum of top drivers shekel vs total delta
    top_delta_sum = round(sum(d["delta_abs"] for d in top_drivers), 2)
    other_delta = round(total_delta - top_delta_sum, 2) if len(drivers) > len(top_drivers) else 0.0

    return {
        "month": month_str,
        "month_display": _month_display(month_str),
        "previous_month": prev_month,
        "previous_month_display": _month_display(prev_month),
        "previous_total": round(prev_total, 2),
        "current_total": round(curr_total, 2),
        "total_delta": round(total_delta, 2),
        "total_delta_pct": round((total_delta / abs(prev_total)) * 100, 1) if prev_total else None,
        "drivers": top_drivers,
        "drivers_count": len(drivers),
        "other_drivers_delta": other_delta,
        "has_prev_month": bool(prev_by_code),
    }


# ──────────────────────────────────────────────────────────
# ENDPOINT 9 — Explained vs Unexplained Delta Coverage
# ──────────────────────────────────────────────────────────

@router.get("/explained-coverage/{municipality_id}/{month}")
async def get_explained_coverage(
    municipality_id: int,
    month: str,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """
    How much of this month's MoM ₪ delta is backed by an approved explanation?

    Per-topic breakdown plus overall coverage ratio. A topic_code is
    "explained" if an ApprovedExplanation exists for (muni, month, code).
    Coverage is measured in shekel:
       explained_delta  = Σ |delta_code| where code is explained
       unexplained_delta = Σ |delta_code| where code is NOT explained
       coverage_ratio   = explained / (explained + unexplained)
    """
    _check_access(current_user, municipality_id)
    _get_municipality(db, municipality_id)

    month_str, _ = _parse_month(month)
    prev_month = (datetime.strptime(month_str, "%Y-%m") - relativedelta(months=1)).strftime("%Y-%m")

    def _sum_by_code(m: str) -> Dict[str, float]:
        rows = (
            db.query(BudgetLine.topic_code, func.sum(BudgetLine.amount).label("total"))
            .filter(
                BudgetLine.municipality_id == municipality_id,
                BudgetLine.current_month == m,
            )
            .group_by(BudgetLine.topic_code)
            .all()
        )
        return {r[0] or "0": float(r[1] or 0.0) for r in rows}

    curr_by_code = _sum_by_code(month_str)
    prev_by_code = _sum_by_code(prev_month)

    # Approved explanations for this month — group by topic_code, keep
    # created_at so we can flag potentially-stale explanations.
    approvals = (
        db.query(ApprovedExplanation.topic_code, ApprovedExplanation.created_at)
        .filter(
            ApprovedExplanation.municipality_id == municipality_id,
            ApprovedExplanation.month == month_str,
        )
        .all()
    )
    explained_codes: set[str] = {r[0] for r in approvals if r[0]}
    approval_created_at: Dict[str, Any] = {r[0]: r[1] for r in approvals if r[0]}
    # An explanation is "potentially stale" when it exists but the underlying
    # delta_pct is ≥10% AND the approval is older than 14 days — meaning the
    # data likely moved after the CPA signed off on the text.
    stale_cutoff = datetime.utcnow() - relativedelta(days=14)

    by_code: List[Dict[str, Any]] = []
    explained_delta_sum = 0.0
    unexplained_delta_sum = 0.0
    total_delta_abs = 0.0

    stale_count = 0
    for code in set(curr_by_code) | set(prev_by_code):
        prev = prev_by_code.get(code, 0.0)
        curr = curr_by_code.get(code, 0.0)
        delta = curr - prev
        if abs(delta) < 0.01:
            continue
        is_explained = code in explained_codes
        delta_abs = abs(delta)
        total_delta_abs += delta_abs
        if is_explained:
            explained_delta_sum += delta_abs
        else:
            unexplained_delta_sum += delta_abs
        # Stale detection: explanation exists but approval date is older than
        # the stale cutoff and the underlying amount has moved materially.
        delta_pct_code = (delta / abs(prev) * 100) if prev else None
        is_stale = False
        if is_explained:
            created = approval_created_at.get(code)
            if created and created < stale_cutoff and delta_pct_code is not None and abs(delta_pct_code) >= 10:
                is_stale = True
                stale_count += 1
        by_code.append({
            "topic_code": code,
            "topic_name": CODE_META.get(code, {}).get("name", f"קוד {code}"),
            "previous_amount": round(prev, 2),
            "current_amount": round(curr, 2),
            "delta_abs": round(delta, 2),
            "delta_pct": round(delta_pct_code, 1) if delta_pct_code is not None else None,
            "is_explained": is_explained,
            "is_naked": (not is_explained) and abs(delta) >= 1000,
            "is_potentially_stale": is_stale,
        })

    # Sort: biggest naked deltas first — that's what the CPA needs to see,
    # then potentially-stale explanations, then everything else.
    by_code.sort(key=lambda r: (not r["is_naked"], not r["is_potentially_stale"], -abs(r["delta_abs"])))

    coverage_ratio = (
        round((explained_delta_sum / total_delta_abs) * 100, 1)
        if total_delta_abs > 0.01 else 100.0
    )
    naked_count = sum(1 for r in by_code if r["is_naked"])

    return {
        "month": month_str,
        "month_display": _month_display(month_str),
        "previous_month": prev_month,
        "previous_month_display": _month_display(prev_month),
        "total_delta_abs": round(total_delta_abs, 2),
        "explained_delta_abs": round(explained_delta_sum, 2),
        "unexplained_delta_abs": round(unexplained_delta_sum, 2),
        "coverage_ratio_pct": coverage_ratio,
        "explained_codes_count": len(explained_codes),
        "naked_codes_count": naked_count,
        "stale_count": stale_count,
        "by_code": by_code,
        "has_prev_month": bool(prev_by_code),
    }


# ──────────────────────────────────────────────────────────
# ENDPOINT 10 — Reconciliation Tie-Out
# ──────────────────────────────────────────────────────────

@router.get("/tie-out/{municipality_id}/{month}")
async def get_tie_out(
    municipality_id: int,
    month: str,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """
    CPA-style reconciliation tie-out:
       Σ budget_lines = invoice_total = breakdown_total ?

    Exposes every number side-by-side so the CPA can sign off on the
    workpaper without re-adding. Flags any tie-break > ₪1 as
    'out_of_balance'.
    """
    _check_access(current_user, municipality_id)
    _get_municipality(db, municipality_id)

    run = _get_run_for_month(db, municipality_id, month)
    if not run:
        raise HTTPException(status_code=404, detail="לא נמצאו נתונים לחודש המבוקש")

    lines = _get_run_lines(db, run.id)
    sum_of_lines = round(sum(float(l.amount or 0.0) for l in lines), 2)
    sum_of_regular = round(sum(float(l.amount or 0.0) for l in lines if not l.is_retro), 2)
    sum_of_retro = round(sum(float(l.amount or 0.0) for l in lines if l.is_retro), 2)

    invoice_total = round(float(run.invoice_total or 0.0), 2)
    breakdown_total = round(float(run.breakdown_total or 0.0), 2)

    lines_vs_invoice = round(sum_of_lines - invoice_total, 2)
    lines_vs_breakdown = round(sum_of_lines - breakdown_total, 2)
    invoice_vs_breakdown = round(invoice_total - breakdown_total, 2)

    tolerance = 1.0  # ₪1 rounding tolerance
    is_balanced = (
        abs(lines_vs_invoice) <= tolerance
        and abs(lines_vs_breakdown) <= tolerance
        and abs(invoice_vs_breakdown) <= tolerance
    )

    # Classify the largest break
    max_break = max(abs(lines_vs_invoice), abs(lines_vs_breakdown), abs(invoice_vs_breakdown))
    if max_break <= tolerance:
        severity = "ok"
    elif max_break <= 100:
        severity = "minor"  # rounding-ish
    elif max_break <= 10000:
        severity = "material"
    else:
        severity = "critical"

    return {
        "municipality_id": municipality_id,
        "month": month,
        "month_display": _month_display(month),
        "run_id": run.id,
        "lines_count": len(lines),
        "sum_of_lines": sum_of_lines,
        "sum_of_regular": sum_of_regular,
        "sum_of_retro": sum_of_retro,
        "invoice_total": invoice_total,
        "breakdown_total": breakdown_total,
        "breaks": {
            "lines_vs_invoice": lines_vs_invoice,
            "lines_vs_breakdown": lines_vs_breakdown,
            "invoice_vs_breakdown": invoice_vs_breakdown,
            "max_abs_break": round(max_break, 2),
        },
        "is_balanced": is_balanced,
        "severity": severity,
        "tolerance": tolerance,
    }


# ──────────────────────────────────────────────────────────
# ENDPOINT 11 — Peer benchmark (compare muni to peers)
# ──────────────────────────────────────────────────────────

@router.get("/peer-benchmark/{municipality_id}/{month}")
async def get_peer_benchmark(
    municipality_id: int,
    month: str,
    include_test: bool = False,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """
    Per-topic peer benchmark: compare this municipality's ₪ for the given
    month against the median / average of all other municipalities that
    filed for the same month.

    Also reports a deviation score (z-score-ish: (muni - median) / median)
    so the CPA can spot "this muni is 60% above its peers on code 19".
    """
    _check_access(current_user, municipality_id)
    me = _get_municipality(db, municipality_id)

    month_str, _ = _parse_month(month)

    # All municipalities (optionally excluding test ones)
    peers_q = db.query(Municipality)
    if not include_test:
        peers_q = peers_q.filter(Municipality.is_test == False)  # noqa: E712
    peers = peers_q.all()

    # Pre-aggregate: for each muni, build {topic_code: sum(amount)} for the month
    per_muni: Dict[int, Dict[str, float]] = {}
    for m in peers:
        run = _get_run_for_month(db, m.id, month_str)
        if not run:
            continue
        lines = _get_run_lines(db, run.id)
        bucket: Dict[str, float] = {}
        for l in lines:
            code = l.topic_code or "0"
            bucket[code] = bucket.get(code, 0.0) + float(l.amount or 0.0)
        if bucket:
            per_muni[m.id] = bucket

    my_bucket = per_muni.get(municipality_id, {})
    peer_ids = [mid for mid in per_muni.keys() if mid != municipality_id]
    peer_count = len(peer_ids)

    # All codes seen across me + peers
    all_codes: set[str] = set(my_bucket.keys())
    for mid in peer_ids:
        all_codes.update(per_muni[mid].keys())

    def _median(values: List[float]) -> float:
        if not values:
            return 0.0
        vs = sorted(values)
        n = len(vs)
        mid = n // 2
        if n % 2:
            return vs[mid]
        return (vs[mid - 1] + vs[mid]) / 2.0

    rows: List[Dict[str, Any]] = []
    for code in sorted(all_codes):
        peer_vals = [per_muni[mid].get(code, 0.0) for mid in peer_ids]
        # Only keep non-zero peers in the benchmark (zero means "didn't file this code")
        peer_nonzero = [v for v in peer_vals if abs(v) > 0.01]
        if not peer_nonzero and abs(my_bucket.get(code, 0.0)) < 0.01:
            continue
        median = round(_median(peer_nonzero), 2)
        avg = round(sum(peer_nonzero) / len(peer_nonzero), 2) if peer_nonzero else 0.0
        mn = round(min(peer_nonzero), 2) if peer_nonzero else 0.0
        mx = round(max(peer_nonzero), 2) if peer_nonzero else 0.0
        mine = round(my_bucket.get(code, 0.0), 2)
        # Deviation from median as a % — positive = we're above peers
        if abs(median) > 0.01:
            deviation_pct = round(((mine - median) / abs(median)) * 100, 1)
        else:
            deviation_pct = None
        # Flag outliers: > 30% away from median on either side
        flag = None
        if deviation_pct is not None:
            if deviation_pct >= 30:
                flag = "above_peers"
            elif deviation_pct <= -30:
                flag = "below_peers"
        rows.append({
            "topic_code": code,
            "topic_name": CODE_META.get(code, {}).get("name", f"קוד {code}"),
            "my_amount": mine,
            "peer_median": median,
            "peer_avg": avg,
            "peer_min": mn,
            "peer_max": mx,
            "peer_count": len(peer_nonzero),
            "deviation_pct": deviation_pct,
            "flag": flag,
        })

    # Sort by |deviation_pct| desc so outliers float to the top
    rows.sort(key=lambda r: -(abs(r["deviation_pct"]) if r["deviation_pct"] is not None else 0))

    outlier_count = sum(1 for r in rows if r["flag"] in ("above_peers", "below_peers"))

    return {
        "municipality_id": municipality_id,
        "municipality_name": me.name,
        "month": month_str,
        "month_display": _month_display(month_str),
        "peer_count": peer_count,
        "has_peer_data": peer_count > 0,
        "outlier_count": outlier_count,
        "by_code": rows,
    }


# ──────────────────────────────────────────────────────────
# ENDPOINT 12 — Formula variance (purple booklet: expected vs actual)
# ──────────────────────────────────────────────────────────

@router.get("/formula-variance/{municipality_id}/{month}")
async def get_formula_variance(
    municipality_id: int,
    month: str,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """
    Compare what the Purple-Booklet formula says we should be paying
    (CHILD_RATE × num_children, per topic category) vs. what was
    actually reported in the budget lines.

    The arithmetic here is what the CPA used to do by hand: "125 normal
    kids × 3,820 = 477,500, but the file says 501,000 — that's +4.9%
    off formula."
    """
    _check_access(current_user, municipality_id)
    me = _get_municipality(db, municipality_id)

    run = _get_run_for_month(db, municipality_id, month)
    if not run:
        raise HTTPException(status_code=404, detail="לא נמצאו נתונים לחודש המבוקש")

    lines = _get_run_lines(db, run.id)

    # Bucket lines by topic_code
    by_code: Dict[str, Dict[str, Any]] = {}
    for l in lines:
        code = l.topic_code or "0"
        b = by_code.setdefault(code, {
            "topic_code": code,
            "topic_name": CODE_META.get(code, {}).get("name", f"קוד {code}"),
            "actual_amount": 0.0,
            "actual_regular": 0.0,
            "actual_retro": 0.0,
            "num_children_reported": 0,
            "lines_count": 0,
        })
        amt = float(l.amount or 0.0)
        b["actual_amount"] += amt
        if l.is_retro:
            b["actual_retro"] += amt
        else:
            b["actual_regular"] += amt
        if l.num_children:
            b["num_children_reported"] = max(b["num_children_reported"], int(l.num_children))
        b["lines_count"] += 1

    # For each code with a known rate-per-child in the purple booklet, compute
    # an "expected" using the reported num_children (if any) or an estimate
    # from the regular portion.
    rows: List[Dict[str, Any]] = []
    grand_expected = 0.0
    grand_actual_regular = 0.0
    for code, b in by_code.items():
        rule = BUDGET_TOPIC_RULES.get(code) if isinstance(BUDGET_TOPIC_RULES, dict) else None
        # Topic 3 uses normal rate; topic 33/19/5 we treat as "no formula rate"
        # unless purple-booklet rules provide one. Default fallback is the
        # 'normal' child rate for kindergarten topics.
        rate = None
        children_basis = "reported"
        if code == "3":
            rate = CHILD_RATE.get("normal")
        elif rule and isinstance(rule, dict):
            # If the purple booklet rule exposes an explicit per-child rate,
            # honour it. Otherwise leave rate=None (we'll skip formula calc).
            rate = rule.get("rate_per_child")
        kids_used = b["num_children_reported"]
        # NOTE: We deliberately do NOT estimate kids from the regular amount.
        # Dividing the amount by the rate and then multiplying back gives a
        # tautological 0% variance — it looks like a successful tie-out but
        # actually checks nothing. Only run the formula when the source file
        # reported an explicit num_children value.
        if rate and kids_used > 0:
            expected = round(float(rate) * float(kids_used), 2)
            variance_abs = round(b["actual_regular"] - expected, 2)
            variance_pct = round(((b["actual_regular"] - expected) / expected) * 100, 1) if expected else None
            # Flag: > 5% off formula is "material"; > 15% is "critical"
            if variance_pct is None:
                flag = None
            elif abs(variance_pct) <= 5:
                flag = "in_line"
            elif abs(variance_pct) <= 15:
                flag = "material"
            else:
                flag = "critical"
            grand_expected += expected
            grand_actual_regular += b["actual_regular"]
            rows.append({
                "topic_code": code,
                "topic_name": b["topic_name"],
                "num_children": kids_used,
                "children_basis": children_basis,
                "rate_per_child": float(rate),
                "expected_amount": expected,
                "actual_regular": round(b["actual_regular"], 2),
                "actual_retro": round(b["actual_retro"], 2),
                "actual_amount": round(b["actual_amount"], 2),
                "variance_abs": variance_abs,
                "variance_pct": variance_pct,
                "flag": flag,
                "formula": f"{kids_used} × ₪{float(rate):,.0f} = ₪{expected:,.0f}",
            })
        else:
            # Can't compute formula for this code — still surface it so the CPA
            # knows the coverage is partial. Distinguish two reasons:
            #   no_children_data → we know the rate, but the source file did
            #                      not report a num_children for this code.
            #   no_formula        → the purple booklet doesn't define a
            #                      per-child rate for this topic.
            missing_reason = "no_children_data" if rate else "no_formula"
            rows.append({
                "topic_code": code,
                "topic_name": b["topic_name"],
                "num_children": kids_used or None,
                "children_basis": children_basis,
                "rate_per_child": float(rate) if rate else None,
                "expected_amount": None,
                "actual_regular": round(b["actual_regular"], 2),
                "actual_retro": round(b["actual_retro"], 2),
                "actual_amount": round(b["actual_amount"], 2),
                "variance_abs": None,
                "variance_pct": None,
                "flag": missing_reason,
                "formula": None,
            })

    # Sort: formula rows first (ranked by |variance_pct|), then no-formula rows
    rows.sort(key=lambda r: (
        r["variance_pct"] is None,
        -(abs(r["variance_pct"]) if r["variance_pct"] is not None else 0),
    ))

    total_variance_abs = round(grand_actual_regular - grand_expected, 2)
    total_variance_pct = (
        round(((grand_actual_regular - grand_expected) / grand_expected) * 100, 1)
        if grand_expected else None
    )
    material_count = sum(1 for r in rows if r["flag"] in ("material", "critical"))

    return {
        "municipality_id": municipality_id,
        "municipality_name": me.name,
        "month": month,
        "month_display": _month_display(month),
        "expected_total": round(grand_expected, 2),
        "actual_regular_total": round(grand_actual_regular, 2),
        "variance_abs": total_variance_abs,
        "variance_pct": total_variance_pct,
        "material_count": material_count,
        "by_code": rows,
    }


# ──────────────────────────────────────────────────────────
# ENDPOINT — Formula-variance drill-down (Phase 3.2)
# ──────────────────────────────────────────────────────────
def _find_prior_run(db: Session, run: MonthlyRun) -> Optional[MonthlyRun]:
    """Most recent processed run for the same municipality, strictly older
    than ``run`` by (month, uploaded_at)."""
    return (
        db.query(MonthlyRun)
        .filter(
            MonthlyRun.municipality_id == run.municipality_id,
            MonthlyRun.id != run.id,
            MonthlyRun.month < run.month,
            MonthlyRun.status == "processed",
        )
        .order_by(MonthlyRun.month.desc(), MonthlyRun.uploaded_at.desc())
        .first()
    )


def _topic_amount_totals(db: Session, run_id: int, topic_code: str) -> Dict[str, float]:
    """Return (regular, retro, total) sums for one topic across all lines
    in a run."""
    lines = (
        db.query(BudgetLine)
        .filter(
            BudgetLine.run_id == run_id,
            BudgetLine.topic_code == str(topic_code),
        )
        .all()
    )
    total = 0.0
    regular = 0.0
    retro = 0.0
    num_children = None
    for ln in lines:
        amt = float(ln.amount or 0.0)
        total += amt
        if ln.is_retro:
            retro += amt
        else:
            regular += amt
        if ln.num_children is not None:
            # Use max — the aggregator already compressed these
            num_children = max(num_children or 0, int(ln.num_children))
    return {
        "total": round(total, 2),
        "regular": round(regular, 2),
        "retro": round(retro, 2),
        "num_children": num_children,
    }


def _enrollment_by_institution(db: Session, run_id: int) -> Dict[str, Dict[str, Any]]:
    """Aggregate ClassEnrollment rows for a run by (institution_code).

    Returns ``{inst_code: {name, total_students, classes}}`` summed across
    all classes and school-year months reported for that run. This is the
    authoritative "how many kids in each school did the formula see" view.
    """
    rows = (
        db.query(ClassEnrollment)
        .filter(ClassEnrollment.run_id == run_id)
        .all()
    )
    by_inst: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        code = str(r.institution_code)
        bucket = by_inst.setdefault(code, {
            "institution_code": code,
            "institution_name": r.institution_name or None,
            "total_students": 0,
            "classes": 0,
        })
        if r.student_count is not None:
            bucket["total_students"] += int(r.student_count)
        bucket["classes"] += 1
        if not bucket["institution_name"] and r.institution_name:
            bucket["institution_name"] = r.institution_name
    return by_inst


def _positions_by_role(db: Session, run_id: int) -> Dict[str, Dict[str, Any]]:
    """Aggregate StaffPosition rows for a run by role (across scopes)."""
    rows = (
        db.query(StaffPosition)
        .filter(StaffPosition.run_id == run_id)
        .all()
    )
    by_role: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        role = str(r.role or "").strip() or "(unknown)"
        bucket = by_role.setdefault(role, {
            "role": role,
            "scope": r.scope,
            "total_fte": 0.0,
            "entries": 0,
        })
        bucket["total_fte"] += float(r.fte or 0.0)
        bucket["entries"] += 1
    return by_role


def _role_matches_topic(role: str, topic_code: str) -> bool:
    """Heuristic: which staff roles are relevant to which budget topic.

    Code 19 (עוזרות גננות) → roles containing "עוזר" or "גננת-קיזוז"
    Code 33 (גננות מדינה)  → roles containing "גננת" (excluding קיזוז)
    Code 5/45 (קב"ס)      → roles containing "קב\"ס" / "ביקור"
    Default               → False (no position driver for this topic)
    """
    role = (role or "").strip()
    tc = str(topic_code)
    if tc == "19":
        return "עוזר" in role or "קיזוז" in role
    if tc == "33":
        return "גננת" in role and "קיזוז" not in role
    if tc in ("5", "45"):
        return "קב" in role or "ביקור" in role
    return False


@router.get("/formula-drivers/{run_id}/{topic_code}")
async def get_formula_drivers(
    run_id: int,
    topic_code: str,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Phase 3.2: Formula-variance drill-down for one topic.

    Decomposes the amount change for a single topic between the current
    run and the most recent prior run into three named drivers:

    * **Enrollment Δ** — how many pupils moved (via ClassEnrollment rows
      from ICHLUSKITOT joined across runs).
    * **Position Δ**  — how many FTEs moved (via StaffPosition rows from
      MISROT + MISROTGY).
    * **Rate Δ**     — residual that can't be explained by count or
      headcount: amount-per-unit drift (e.g., a policy rate change).

    The UI uses this to answer: "The גני ילדים line went up ₪12,400 —
    was it because 3 more kids enrolled, or because the rate per child
    went up, or because we're paying for more assistants?"
    """
    run = db.query(MonthlyRun).filter(MonthlyRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="ריצה לא נמצאה")
    _check_access(current_user, run.municipality_id)

    muni = _get_municipality(db, run.municipality_id)
    prior_run = _find_prior_run(db, run)

    curr = _topic_amount_totals(db, run.id, topic_code)
    prev = (
        _topic_amount_totals(db, prior_run.id, topic_code)
        if prior_run
        else {"total": 0.0, "regular": 0.0, "retro": 0.0, "num_children": None}
    )

    delta_amount = round(curr["total"] - prev["total"], 2)
    delta_regular = round(curr["regular"] - prev["regular"], 2)
    delta_pct = (
        round((delta_amount / prev["total"]) * 100, 2)
        if prev["total"] else None
    )

    # ── Enrollment Δ (ICHLUSKITOT) ───────────────────────────
    curr_enroll = _enrollment_by_institution(db, run.id)
    prev_enroll = _enrollment_by_institution(db, prior_run.id) if prior_run else {}

    all_insts = set(curr_enroll.keys()) | set(prev_enroll.keys())
    enrollment_rows: List[Dict[str, Any]] = []
    for code in sorted(all_insts):
        c = curr_enroll.get(code, {})
        p = prev_enroll.get(code, {})
        c_total = int(c.get("total_students", 0) or 0)
        p_total = int(p.get("total_students", 0) or 0)
        delta = c_total - p_total
        if delta == 0 and c_total == 0 and p_total == 0:
            continue
        enrollment_rows.append({
            "institution_code": code,
            "institution_name": c.get("institution_name") or p.get("institution_name"),
            "prev_students": p_total,
            "curr_students": c_total,
            "delta_students": delta,
        })
    enrollment_rows.sort(key=lambda r: abs(r["delta_students"]), reverse=True)

    enrollment_total_prev = sum(r["prev_students"] for r in enrollment_rows)
    enrollment_total_curr = sum(r["curr_students"] for r in enrollment_rows)
    enrollment_total_delta = enrollment_total_curr - enrollment_total_prev

    # ── Positions Δ (MISROT/MISROTGY) ─────────────────────────
    curr_pos = _positions_by_role(db, run.id)
    prev_pos = _positions_by_role(db, prior_run.id) if prior_run else {}

    all_roles = set(curr_pos.keys()) | set(prev_pos.keys())
    position_rows: List[Dict[str, Any]] = []
    for role in sorted(all_roles):
        c = curr_pos.get(role, {})
        p = prev_pos.get(role, {})
        c_fte = float(c.get("total_fte", 0.0) or 0.0)
        p_fte = float(p.get("total_fte", 0.0) or 0.0)
        delta_fte = round(c_fte - p_fte, 3)
        if abs(delta_fte) < 0.001 and abs(c_fte) < 0.001 and abs(p_fte) < 0.001:
            continue
        position_rows.append({
            "role": role,
            "scope": c.get("scope") or p.get("scope"),
            "prev_fte": round(p_fte, 3),
            "curr_fte": round(c_fte, 3),
            "delta_fte": delta_fte,
            "relevant_to_topic": _role_matches_topic(role, topic_code),
        })
    position_rows.sort(key=lambda r: (not r["relevant_to_topic"], -abs(r["delta_fte"])))

    # Only count "relevant" roles in totals — other FTE moves belong to
    # other topics.
    relevant_positions = [r for r in position_rows if r["relevant_to_topic"]]
    position_total_prev = round(sum(r["prev_fte"] for r in relevant_positions), 3)
    position_total_curr = round(sum(r["curr_fte"] for r in relevant_positions), 3)
    position_total_delta = round(position_total_curr - position_total_prev, 3)

    # ── Rate Δ (derived) ──────────────────────────────────────
    # For enrollment-driven topics, rate = amount / num_children.
    # Prefer the budget-line-reported num_children; fall back to the
    # ICHLUSKITOT enrollment total when the aggregated line hasn't
    # captured a count. For position-driven topics, fall back to the
    # relevant FTE totals so we still get a rate-per-unit signal.
    prev_kids = prev.get("num_children") or (enrollment_total_prev if enrollment_total_prev > 0 else None)
    curr_kids = curr.get("num_children") or (enrollment_total_curr if enrollment_total_curr > 0 else None)
    kids_source = "budget_line" if (prev.get("num_children") or curr.get("num_children")) else "enrollment_total"

    prev_rate_per_kid = (
        prev["regular"] / prev_kids if prev_kids else None
    )
    curr_rate_per_kid = (
        curr["regular"] / curr_kids if curr_kids else None
    )
    rate_delta_kids = (
        round(curr_rate_per_kid - prev_rate_per_kid, 2)
        if (prev_rate_per_kid is not None and curr_rate_per_kid is not None)
        else None
    )

    # Position-based rate (amount / relevant FTE)
    prev_rate_per_fte = (
        prev["regular"] / position_total_prev if position_total_prev else None
    )
    curr_rate_per_fte = (
        curr["regular"] / position_total_curr if position_total_curr else None
    )
    rate_delta_fte = (
        round(curr_rate_per_fte - prev_rate_per_fte, 2)
        if (prev_rate_per_fte is not None and curr_rate_per_fte is not None)
        else None
    )

    # Explained decomposition (best-effort — requires both kids known)
    explained = None
    if prev_kids and curr_kids and prev_rate_per_kid is not None:
        from_enrollment = round(prev_rate_per_kid * (curr_kids - prev_kids), 2)
        from_rate = round((curr_rate_per_kid - prev_rate_per_kid) * curr_kids, 2) if curr_rate_per_kid is not None else 0.0
        residual = round(delta_regular - from_enrollment - from_rate, 2)
        explained = {
            "delta_regular": delta_regular,
            "from_enrollment": from_enrollment,
            "from_rate": from_rate,
            "residual": residual,
            "kids_source": kids_source,
        }

    return {
        "run_id": run.id,
        "municipality_id": muni.id,
        "municipality_name": muni.name,
        "month": run.month,
        "topic_code": str(topic_code),
        "topic_name": CODE_META.get(str(topic_code), {}).get("name"),
        "previous_run_id": prior_run.id if prior_run else None,
        "previous_month": prior_run.month if prior_run else None,
        "amount": {
            "prev_total": prev["total"],
            "curr_total": curr["total"],
            "delta_total": delta_amount,
            "prev_regular": prev["regular"],
            "curr_regular": curr["regular"],
            "delta_regular": delta_regular,
            "delta_pct": delta_pct,
        },
        "enrollment_delta": {
            "prev_total": enrollment_total_prev,
            "curr_total": enrollment_total_curr,
            "delta_total": enrollment_total_delta,
            "prev_num_children_from_budget": prev_kids,
            "curr_num_children_from_budget": curr_kids,
            "by_institution": enrollment_rows,
        },
        "positions_delta": {
            "prev_total_fte": position_total_prev,
            "curr_total_fte": position_total_curr,
            "delta_total_fte": position_total_delta,
            "by_role": position_rows,
        },
        "rate_delta": {
            "prev_rate_per_child": (
                round(prev_rate_per_kid, 2) if prev_rate_per_kid is not None else None
            ),
            "curr_rate_per_child": (
                round(curr_rate_per_kid, 2) if curr_rate_per_kid is not None else None
            ),
            "delta_rate_per_child": rate_delta_kids,
            "kids_source": kids_source,
            "prev_rate_per_fte": (
                round(prev_rate_per_fte, 2) if prev_rate_per_fte is not None else None
            ),
            "curr_rate_per_fte": (
                round(curr_rate_per_fte, 2) if curr_rate_per_fte is not None else None
            ),
            "delta_rate_per_fte": rate_delta_fte,
        },
        "explained": explained,
    }


# ──────────────────────────────────────────────────────────
# Phase 3.3: Route-level transportation audit
# ──────────────────────────────────────────────────────────
def _routes_by_key(
    db: Session,
    run_id: int,
    topic_code: str,
    period_month: Optional[int] = None,
    period_year: Optional[int] = None,
) -> Dict[str, Dict[str, Any]]:
    """Aggregate transport routes for a run by route identity.

    Each physical route (route_number + direction + vehicle_code) may
    appear with multiple period_month rows within a single budget run.
    We sum calculated_total across those months and expose the months
    covered as a list so the UI can show "route 301000 appears Sep-Jun".

    If period_month/period_year are given, only rows matching that
    period are aggregated.
    """
    q = db.query(TransportRoute).filter(
        TransportRoute.run_id == run_id,
        TransportRoute.topic_code == str(topic_code),
    )
    if period_month is not None:
        q = q.filter(TransportRoute.period_month == period_month)
    if period_year is not None:
        q = q.filter(TransportRoute.period_year == period_year)

    rows = q.all()
    idx: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        key = f"{r.route_number or '—'}::{r.direction or ''}::{r.vehicle_code or ''}"
        bucket = idx.get(key)
        if bucket is None:
            bucket = {
                "route_number": r.route_number,
                "route_type": r.route_type,
                "payment_group": r.payment_group,
                "period": r.period,
                "direction": r.direction,
                "company_code": r.company_code,
                "company_name": r.company_name,
                "localities": r.localities,
                "institutions": r.institutions,
                "vehicle_code": r.vehicle_code,
                "vehicle_type": r.vehicle_type,
                "license_plate": r.license_plate,
                "days": r.days,
                "vehicle_count": r.vehicle_count,
                "km_per_trip": r.km_per_trip,
                "daily_cost": r.daily_cost,
                "participation_pct": r.participation_pct,
                "vat_factor": r.vat_factor,
                "escalation": r.escalation,
                "calculated_total": 0.0,
                "period_months": [],
                "notes": r.notes,
            }
            idx[key] = bucket
        bucket["calculated_total"] += float(r.calculated_total or 0.0)
        if r.period_month is not None:
            bucket["period_months"].append({
                "year": r.period_year,
                "month": r.period_month,
            })
    # Sort period_months chronologically for display
    for bucket in idx.values():
        bucket["period_months"].sort(key=lambda m: (m.get("year") or 0, m.get("month") or 0))
        bucket["month_count"] = len(bucket["period_months"])
    return idx


@router.get("/transport-routes/{run_id}/{topic_code}")
async def get_transport_routes(
    run_id: int,
    topic_code: str,
    period_month: Optional[int] = None,
    period_year: Optional[int] = None,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Phase 3.3: Route-level transportation audit for one topic.

    Returns the full route list for the current run (topic 52 = regular
    transport, topic 140 = special-ed transport), enriched with the prior
    run's calculated_total for the same route so the UI can show a per-
    route Δ ranked by impact.

    Also returns a company summary (calculated_total rollup by vendor)
    and a vehicle-type summary, to answer "which vendor / class of
    vehicle drove the transportation change?"

    Optional query params `period_month` and `period_year` narrow the
    response to a single application month (e.g., to isolate the route
    costs booked for 2025-03 within a budget run that covers many
    months).
    """
    if str(topic_code) not in {"52", "140"}:
        raise HTTPException(
            status_code=400,
            detail="נתוני מסלולים זמינים רק עבור קודי הסעה (52, 140)",
        )

    run = db.query(MonthlyRun).filter(MonthlyRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="ריצה לא נמצאה")
    _check_access(current_user, run.municipality_id)

    muni = _get_municipality(db, run.municipality_id)
    prior_run = _find_prior_run(db, run)

    curr_routes = _routes_by_key(db, run.id, topic_code, period_month, period_year)
    prev_routes = (
        _routes_by_key(db, prior_run.id, topic_code, period_month, period_year)
        if prior_run
        else {}
    )

    # Build per-route rows (union of keys)
    all_keys = set(curr_routes.keys()) | set(prev_routes.keys())
    route_rows: List[Dict[str, Any]] = []
    for key in all_keys:
        c = curr_routes.get(key)
        p = prev_routes.get(key)
        c_total = float((c or {}).get("calculated_total") or 0.0)
        p_total = float((p or {}).get("calculated_total") or 0.0)
        delta = round(c_total - p_total, 2)
        # Status: new / dropped / changed / unchanged
        if c is None:
            status = "dropped"
        elif p is None:
            status = "new"
        elif abs(delta) < 0.01:
            status = "unchanged"
        else:
            status = "changed"
        src = c or p  # prefer current, fall back to prior for identity
        route_rows.append({
            **{k: src.get(k) for k in (
                "route_number", "route_type", "payment_group", "period",
                "direction", "company_code", "company_name",
                "localities", "institutions",
                "vehicle_code", "vehicle_type", "license_plate",
                "days", "vehicle_count", "km_per_trip", "daily_cost",
                "participation_pct", "vat_factor", "escalation",
                "notes",
            )},
            "curr_period_months": (c or {}).get("period_months", []),
            "prev_period_months": (p or {}).get("period_months", []),
            "curr_month_count": (c or {}).get("month_count", 0),
            "prev_month_count": (p or {}).get("month_count", 0),
            "prev_total": round(p_total, 2),
            "curr_total": round(c_total, 2),
            "delta_total": delta,
            "status": status,
        })

    # Sort by abs(delta) desc so top movers float to top
    route_rows.sort(key=lambda r: -abs(r["delta_total"]))

    # Company summary (rollup on current run)
    by_company: Dict[str, Dict[str, Any]] = {}
    for r in route_rows:
        co = r.get("company_code") or "—"
        co_name = r.get("company_name") or "—"
        bucket = by_company.setdefault(co, {
            "company_code": co,
            "company_name": co_name,
            "route_count": 0,
            "curr_total": 0.0,
            "prev_total": 0.0,
            "delta_total": 0.0,
        })
        bucket["route_count"] += 1
        bucket["curr_total"] += r["curr_total"]
        bucket["prev_total"] += r["prev_total"]
        bucket["delta_total"] += r["delta_total"]
    for b in by_company.values():
        b["curr_total"] = round(b["curr_total"], 2)
        b["prev_total"] = round(b["prev_total"], 2)
        b["delta_total"] = round(b["delta_total"], 2)
    by_company_list = sorted(by_company.values(), key=lambda b: -abs(b["delta_total"]))

    # Vehicle-type summary
    by_vehicle: Dict[str, Dict[str, Any]] = {}
    for r in route_rows:
        vt = r.get("vehicle_type") or "—"
        bucket = by_vehicle.setdefault(vt, {
            "vehicle_type": vt,
            "route_count": 0,
            "curr_total": 0.0,
            "prev_total": 0.0,
            "delta_total": 0.0,
        })
        bucket["route_count"] += 1
        bucket["curr_total"] += r["curr_total"]
        bucket["prev_total"] += r["prev_total"]
        bucket["delta_total"] += r["delta_total"]
    for b in by_vehicle.values():
        b["curr_total"] = round(b["curr_total"], 2)
        b["prev_total"] = round(b["prev_total"], 2)
        b["delta_total"] = round(b["delta_total"], 2)
    by_vehicle_list = sorted(by_vehicle.values(), key=lambda b: -abs(b["delta_total"]))

    # Topline totals
    curr_total = round(sum(r["curr_total"] for r in route_rows), 2)
    prev_total = round(sum(r["prev_total"] for r in route_rows), 2)
    delta_total = round(curr_total - prev_total, 2)

    new_routes = [r for r in route_rows if r["status"] == "new"]
    dropped_routes = [r for r in route_rows if r["status"] == "dropped"]

    return {
        "run_id": run.id,
        "municipality_id": muni.id,
        "municipality_name": muni.name,
        "month": run.month,
        "topic_code": str(topic_code),
        "topic_name": CODE_META.get(str(topic_code), {}).get("name"),
        "previous_run_id": prior_run.id if prior_run else None,
        "previous_month": prior_run.month if prior_run else None,
        "summary": {
            "route_count_curr": len([r for r in route_rows if r["status"] != "dropped"]),
            "route_count_prev": len([r for r in route_rows if r["status"] != "new"]),
            "new_routes": len(new_routes),
            "dropped_routes": len(dropped_routes),
            "curr_total": curr_total,
            "prev_total": prev_total,
            "delta_total": delta_total,
        },
        "by_company": by_company_list,
        "by_vehicle": by_vehicle_list,
        "routes": route_rows,
    }
