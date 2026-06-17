"""
Reports & Documents System — backend/routes/reports.py

Tables:  generated_reports, cpa_branding, report_templates
Endpoints:
  GET  /api/reports/list/{municipality_id}
  GET  /api/reports/download/{report_id}
  POST /api/reports/generate/{municipality_id}/{month}
  GET  /api/reports/generate/comparison/{municipality_id}
  DELETE /api/reports/{report_id}
  GET  /api/reports/admin/all
  POST /api/reports/branding
  GET  /api/reports/branding
  POST /api/reports/templates
  GET  /api/reports/templates
  GET  /api/reports/status/{job_id}
"""

import json
import logging
import os
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote as _urlquote

from fastapi import (APIRouter, BackgroundTasks, Depends,
                     File, Form, HTTPException, UploadFile)
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, DateTime, func
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend.models.municipality import Municipality
from backend.models.monthly_run import MonthlyRun
from backend.models.budget_line import BudgetLine
from backend.models.approved_explanation import ApprovedExplanation
from backend.models.user import User
from backend.utils.auth_guards import require_login

logger = logging.getLogger(__name__)
router = APIRouter(tags=["reports"])

# ──────────────────────────────────────────────────────────────────────────────
# SQLAlchemy Models
# ──────────────────────────────────────────────────────────────────────────────

class GeneratedReport(Base):
    __tablename__ = "generated_reports"
    __table_args__ = {"extend_existing": True}

    id                = Column(Integer, primary_key=True, autoincrement=True)
    municipality_id   = Column(Integer, nullable=False, index=True)
    municipality_name = Column(String, nullable=False, default="")
    month             = Column(String, nullable=True)
    report_type       = Column(String, default="monthly")   # monthly|comparison|custom|positions
    file_path         = Column(String, nullable=True)
    file_name         = Column(String, nullable=True)
    file_size         = Column(Integer, default=0)
    generated_by      = Column(String, default="auto")      # "auto" or user_id string
    generated_at      = Column(DateTime, default=datetime.utcnow)
    download_count    = Column(Integer, default=0)
    is_auto_generated = Column(Boolean, default=False)
    custom_config     = Column(Text, default="{}")          # JSON


class CPABranding(Base):
    __tablename__ = "cpa_branding"
    __table_args__ = {"extend_existing": True}

    id               = Column(Integer, primary_key=True, autoincrement=True)
    logo_path        = Column(String, nullable=True)
    firm_name        = Column(String, default="")
    firm_address     = Column(String, default="")
    firm_phone       = Column(String, default="")
    firm_email       = Column(String, default="")
    primary_color    = Column(String, default="#1E3A5F")
    secondary_color  = Column(String, default="#3B82F6")
    report_footer_text = Column(String, default="")
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by       = Column(Integer, nullable=True)


class ReportTemplate(Base):
    __tablename__ = "report_templates"
    __table_args__ = {"extend_existing": True}

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String, nullable=False)
    description = Column(String, default="")
    config      = Column(Text, default="{}")   # JSON
    created_by  = Column(Integer, nullable=True)
    is_default  = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────────────
# Table creation
# ──────────────────────────────────────────────────────────────────────────────

def init_reports(db: Session):
    """Create report tables and ensure reports directory exists."""
    Base.metadata.create_all(bind=engine, tables=[
        GeneratedReport.__table__,
        CPABranding.__table__,
        ReportTemplate.__table__,
    ])
    os.makedirs(os.path.join('backend', 'reports'), exist_ok=True)
    logger.info("Reports system initialized")


# ──────────────────────────────────────────────────────────────────────────────
# Background job registry (in-memory)
# ──────────────────────────────────────────────────────────────────────────────

_JOBS: Dict[str, Dict] = {}  # job_id → {status, report_id, error}
_JOBS_LOCK = threading.Lock()


def _set_job(job_id: str, **kwargs):
    with _JOBS_LOCK:
        _JOBS.setdefault(job_id, {}).update(kwargs)


# ──────────────────────────────────────────────────────────────────────────────
# Data helpers
# ──────────────────────────────────────────────────────────────────────────────

_HEB_MONTHS = {
    '01': 'ינואר', '02': 'פברואר', '03': 'מרץ',    '04': 'אפריל',
    '05': 'מאי',   '06': 'יוני',   '07': 'יולי',    '08': 'אוגוסט',
    '09': 'ספטמבר','10': 'אוקטובר','11': 'נובמבר',  '12': 'דצמבר',
}

def _month_display(m: str) -> str:
    if not m:
        return ''
    try:
        y, mo = m[:4], m[5:7]
        return f"{_HEB_MONTHS.get(mo, mo)} {y}"
    except Exception:
        return m


def _file_size_display(n: int) -> str:
    if not n:
        return '0 B'
    for unit in ['B', 'KB', 'MB']:
        if n < 1024:
            return f'{n:.0f} {unit}'
        n /= 1024
    return f'{n:.1f} GB'


def _get_branding_dict(db: Session) -> Optional[Dict]:
    brand = db.query(CPABranding).first()
    if not brand:
        return None
    return {
        'logo_path': brand.logo_path or '',
        'firm_name': brand.firm_name or '',
        'firm_address': brand.firm_address or '',
        'firm_phone': brand.firm_phone or '',
        'firm_email': brand.firm_email or '',
        'primary_color': brand.primary_color or '#1E3A5F',
        'secondary_color': brand.secondary_color or '#3B82F6',
        'report_footer_text': brand.report_footer_text or '',
    }


def _is_real_line(line) -> bool:
    """
    Match backend/routes/analytics.py::_is_real_line — filter out blank
    placeholder rows (empty topic, zero amount, code '0' or empty) so they
    don't pollute totals, YTD tables, or code breakdowns.
    """
    code = (line.topic_code or '').strip()
    if not code or code == '0':
        if float(line.amount or 0) == 0 and not (line.budget_topic or '').strip():
            return False
    return True


def _safe_retro_share(retro: float, regular: float) -> float:
    """
    Retro percentage using |retro| / (|retro| + |regular|) so that deduction
    codes (e.g. 33, which is legitimately negative) don't produce >100% or
    <0% retro shares.
    """
    denom = abs(retro) + abs(regular)
    if denom <= 0.01:
        return 0.0
    return round((abs(retro) / denom) * 100, 1)


def _load_budget_data(municipality_id: int, month: str, db: Session) -> Dict:
    """Collect all data needed for PDF generation."""
    run = db.query(MonthlyRun).filter(
        MonthlyRun.municipality_id == municipality_id,
        MonthlyRun.month == month,
    ).first()

    if not run:
        return {}

    raw_lines = db.query(BudgetLine).filter(BudgetLine.run_id == run.id).all()
    lines = [l for l in raw_lines if _is_real_line(l)]

    # Approved explanations dict: topic_code → text
    approved = db.query(ApprovedExplanation).filter(
        ApprovedExplanation.municipality_id == municipality_id,
        ApprovedExplanation.month == month,
    ).all()
    explanations = {str(a.topic_code): a.final_text for a in approved}

    # By-code summary
    from collections import defaultdict
    totals: Dict[str, float] = defaultdict(float)
    code_names: Dict[str, str] = {}
    retro_total = 0.0

    lines_as_dicts = []
    for l in lines:
        d = {
            'id': l.id,
            'budget_topic': l.budget_topic,
            'topic_code': l.topic_code,
            'amount': l.amount,
            'period_month': l.period_month,
            'line_type': l.line_type,
            'is_retro': l.is_retro,
            'notes': l.notes or '',
        }
        lines_as_dicts.append(d)
        totals[l.topic_code] += l.amount
        code_names[l.topic_code] = l.budget_topic
        if l.is_retro:
            retro_total += l.amount

    # Calculate previous month for changes
    try:
        y, m = int(month[:4]), int(month[5:7])
        if m == 1:
            prev_month = f'{y - 1}-12'
        else:
            prev_month = f'{y}-{str(m - 1).padStart(2, "0")}'
    except Exception:
        prev_month = None

    # Simpler prev month calc
    try:
        y, m = int(month[:4]), int(month[5:7])
        pm = m - 1
        py = y
        if pm == 0:
            pm = 12
            py -= 1
        prev_month = f'{py}-{str(pm).zfill(2)}'
    except Exception:
        prev_month = None

    # Changes vs previous month
    changes = []
    if prev_month:
        prev_run = db.query(MonthlyRun).filter(
            MonthlyRun.municipality_id == municipality_id,
            MonthlyRun.month == prev_month,
        ).first()
        if prev_run:
            prev_lines = db.query(BudgetLine).filter(BudgetLine.run_id == prev_run.id).all()
            prev_totals: Dict[str, float] = defaultdict(float)
            prev_names: Dict[str, str] = {}
            for pl in prev_lines:
                prev_totals[pl.topic_code] += pl.amount
                prev_names[pl.topic_code] = pl.budget_topic

            all_codes = set(list(totals.keys()) + list(prev_totals.keys()))
            for code in all_codes:
                cur = totals.get(code, 0)
                pre = prev_totals.get(code, 0)
                delta = cur - pre
                pct = (delta / abs(pre) * 100) if pre else None
                if abs(delta) > 0.01:
                    changes.append({
                        'code': code,
                        'name': code_names.get(code) or prev_names.get(code, code),
                        'current_total': cur,
                        'prev_total': pre,
                        'change_amount': delta,
                        'change_pct': pct,
                    })

    # By-code list for summary page
    grand = sum(totals.values()) or 1
    by_code = [
        {
            'code': code,
            'name': name,
            'total': totals[code],
            'pct_of_total': totals[code] / grand * 100,
            'change_pct': next((c['change_pct'] for c in changes if c['code'] == code), None),
        }
        for code, name in code_names.items()
    ]
    by_code.sort(key=lambda x: -abs(x['total']))

    # Anomalies: imbalanced or large retro
    anomalies = []
    if not run.is_balanced:
        anomalies.append({
            'severity': 'high',
            'title': 'חוסר איזון',
            'description': f'הפרש: {run.difference:,.2f} ₪',
            'recommendation': 'יש לבדוק את חשבון הספק',
        })
    if retro_total > 100_000:
        anomalies.append({
            'severity': 'medium',
            'title': 'תשלום רטרו גבוה',
            'description': f'סכום רטרו כולל: {retro_total:,.0f} ₪',
            'recommendation': 'יש לוודא שכל תשלומי הרטרו מוצדקים',
        })

    # ── Tie-out reconciliation ────────────────────────────────────────────
    sum_of_lines = round(sum(l.amount or 0 for l in lines), 2)
    invoice_total_val = round(float(run.invoice_total or 0.0), 2)
    breakdown_total_val = round(float(run.breakdown_total or 0.0), 2)
    lines_vs_invoice = round(sum_of_lines - invoice_total_val, 2)
    lines_vs_breakdown = round(sum_of_lines - breakdown_total_val, 2)
    invoice_vs_breakdown = round(invoice_total_val - breakdown_total_val, 2)
    max_break = max(
        abs(lines_vs_invoice),
        abs(lines_vs_breakdown),
        abs(invoice_vs_breakdown),
    )
    tolerance = 1.0
    tie_out = {
        'sum_of_lines': sum_of_lines,
        'invoice_total': invoice_total_val,
        'breakdown_total': breakdown_total_val,
        'breaks': {
            'lines_vs_invoice': lines_vs_invoice,
            'lines_vs_breakdown': lines_vs_breakdown,
            'invoice_vs_breakdown': invoice_vs_breakdown,
            'max_abs_break': round(max_break, 2),
        },
        'is_balanced': max_break <= tolerance,
    }

    # ── Variance drivers (ranked by absolute shekel impact) ──────────────
    total_delta = sum(c['change_amount'] for c in changes)
    drivers_sorted = sorted(changes, key=lambda c: -abs(c['change_amount']))
    variance_drivers_dict = {
        'has_prev_month': bool(changes),
        'previous_month_display': _month_display(prev_month) if prev_month else '',
        'total_delta': round(total_delta, 2),
        'drivers': [
            {
                'topic_code': c['code'],
                'topic_name': c.get('name') or c['code'],
                'delta_abs': round(c['change_amount'], 2),
                'delta_pct': round(c['change_pct'], 1) if c.get('change_pct') is not None else None,
                'share_of_total_change_pct': (
                    round((c['change_amount'] / total_delta) * 100, 1)
                    if abs(total_delta) > 0.01 else None
                ),
            }
            for c in drivers_sorted[:6]
        ],
    }

    # ── Explained-vs-unexplained coverage ────────────────────────────────
    explained_codes = set(str(k) for k in explanations.keys())
    explained_delta = 0.0
    unexplained_delta = 0.0
    naked_count = 0
    for c in changes:
        d_abs = abs(c['change_amount'])
        if str(c['code']) in explained_codes:
            explained_delta += d_abs
        else:
            unexplained_delta += d_abs
            if d_abs >= 1000:
                naked_count += 1
    total_abs = explained_delta + unexplained_delta
    coverage_ratio = (
        round((explained_delta / total_abs) * 100, 1)
        if total_abs > 0.01 else 100.0
    )
    explained_coverage_dict = {
        'has_prev_month': bool(changes),
        'coverage_ratio_pct': coverage_ratio,
        'explained_delta_abs': round(explained_delta, 2),
        'unexplained_delta_abs': round(unexplained_delta, 2),
        'naked_codes_count': naked_count,
    }

    # ── YTD cumulative per topic (Jan → current month of same year) ───────
    try:
        year_int = int(month[:4])
        ytd_start = f'{year_int}-01'
    except Exception:
        ytd_start = month
    raw_ytd_lines = db.query(BudgetLine).filter(
        BudgetLine.municipality_id == municipality_id,
        BudgetLine.current_month >= ytd_start,
        BudgetLine.current_month <= month,
    ).all()
    ytd_lines = [l for l in raw_ytd_lines if _is_real_line(l)]
    ytd_by_code: Dict[str, Dict[str, float]] = {}
    ytd_total_val = 0.0
    ytd_retro_val = 0.0
    ytd_months: set = set()
    for yl in ytd_lines:
        code = yl.topic_code or '0'
        amt = float(yl.amount or 0.0)
        ytd_months.add(yl.current_month)
        bucket = ytd_by_code.setdefault(code, {
            'topic_code': code,
            'topic_name': yl.budget_topic or code,
            'ytd_total': 0.0,
            'ytd_retro': 0.0,
            'months': set(),
        })
        bucket['ytd_total'] += amt
        bucket['months'].add(yl.current_month)
        if yl.is_retro:
            bucket['ytd_retro'] += amt
            ytd_retro_val += amt
        ytd_total_val += amt

    ytd_list = []
    for code, b in ytd_by_code.items():
        n_months = len(b['months'])
        regular = b['ytd_total'] - b['ytd_retro']
        ytd_list.append({
            'topic_code': code,
            'topic_name': b['topic_name'],
            'ytd_total': round(b['ytd_total'], 2),
            'ytd_retro': round(b['ytd_retro'], 2),
            'avg_per_month': round(regular / n_months, 2) if n_months else 0.0,
            'retro_share_pct': _safe_retro_share(b['ytd_retro'], regular),
        })
    ytd_list.sort(key=lambda r: -abs(r['ytd_total']))
    n_ytd_months = len(ytd_months)

    # Annual projection + fiscal-year gap (runs in window)
    projected_annual = round(ytd_total_val * (12 / n_ytd_months), 2) if n_ytd_months else 0.0
    pct_of_projected = (
        round((ytd_total_val / projected_annual) * 100, 1)
        if projected_annual else 0.0
    )
    runs_in_window = db.query(MonthlyRun).filter(
        MonthlyRun.municipality_id == municipality_id,
        MonthlyRun.month >= ytd_start,
        MonthlyRun.month <= month,
    ).all()
    fy_due = round(sum(float(r.breakdown_total or 0.0) for r in runs_in_window), 2)
    fy_paid = round(sum(float(r.invoice_total or 0.0) for r in runs_in_window), 2)
    fy_gap = round(fy_due - fy_paid, 2)

    # Smart bullets — computed facts (numbers, not rewriting of prose)
    smart_bullets: List[str] = []
    if ytd_list:
        top3 = ytd_list[:3]
        top3_sum = sum(r['ytd_total'] for r in top3)
        top3_share = (top3_sum / ytd_total_val * 100) if ytd_total_val else 0
        names = ', '.join(f"{r['topic_name']} (₪{r['ytd_total']:,.0f})" for r in top3)
        smart_bullets.append(
            f"שלושת הנושאים הגדולים מצטברים ל-₪{top3_sum:,.0f} "
            f"({top3_share:.1f}% מהסך): {names}"
        )
    if ytd_total_val:
        smart_bullets.append(
            f"תשלומי רטרו: {round((ytd_retro_val / ytd_total_val) * 100, 1)}% "
            f"מסך התקבולים (₪{ytd_retro_val:,.0f})."
        )
    if n_ytd_months and projected_annual:
        smart_bullets.append(
            f"על בסיס {n_ytd_months} חודשים — תחזית שנתית: ₪{projected_annual:,.0f} "
            f"(נצברו עד כה {pct_of_projected}%)."
        )
    if fy_gap:
        sign_word = "עודף" if fy_gap < 0 else "חוסר"
        smart_bullets.append(
            f"פער מצטבר בין מגיע לשולם בשנה: ₪{abs(fy_gap):,.0f} ({sign_word})."
        )

    ytd_dict = {
        'start_month_display': _month_display(ytd_start),
        'end_month_display': _month_display(month),
        'months_covered_count': n_ytd_months,
        'ytd_total': round(ytd_total_val, 2),
        'ytd_retro': round(ytd_retro_val, 2),
        'avg_per_month': round(ytd_total_val / n_ytd_months, 2) if n_ytd_months else 0.0,
        'ytd_retro_share_pct': _safe_retro_share(ytd_retro_val, ytd_total_val - ytd_retro_val),
        'projected_annual': projected_annual,
        'pct_of_projected_annual': pct_of_projected,
        'fiscal_year_due_total': fy_due,
        'fiscal_year_paid_total': fy_paid,
        'fiscal_year_cumulative_gap': fy_gap,
        'smart_bullets': smart_bullets,
        'by_code': ytd_list,
    }

    # ── Peer benchmark (median/avg per topic across other munis this month) ──
    # Build a flat {code: amount} map and a {code: name} map from the by_code list.
    my_flat_totals: Dict[str, float] = {row['code']: float(row['total']) for row in by_code}
    my_flat_names: Dict[str, str] = {row['code']: row['name'] for row in by_code}
    try:
        peer_benchmark_dict = _compute_peer_benchmark(
            db, municipality_id, month, my_flat_totals, my_flat_names
        )
    except Exception as e:
        logger.warning(f"peer_benchmark compute failed: {e}")
        peer_benchmark_dict = None

    # ── Formula variance (Purple-Booklet expected vs actual) ──
    try:
        formula_variance_dict = _compute_formula_variance(lines, my_flat_names)
    except Exception as e:
        logger.warning(f"formula_variance compute failed: {e}")
        formula_variance_dict = None

    return {
        'run': run,
        'lines': lines_as_dicts,
        'explanations': explanations,
        'invoice_total': run.invoice_total or 0,
        'breakdown_total': run.breakdown_total or 0,
        'difference': run.difference or 0,
        'retro_total': retro_total,
        'by_code': by_code,
        'changes': changes,
        'prev_month': prev_month,
        'anomalies': anomalies,
        'tie_out': tie_out,
        'variance_drivers': variance_drivers_dict,
        'explained_coverage': explained_coverage_dict,
        'ytd': ytd_dict,
        'peer_benchmark': peer_benchmark_dict,
        'formula_variance': formula_variance_dict,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Shared compute helpers — peer benchmark + formula variance (mirror analytics.py)
# ──────────────────────────────────────────────────────────────────────────────

def _compute_peer_benchmark(
    db: Session,
    municipality_id: int,
    month: str,
    my_by_code: Dict[str, float],
    code_names: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Build per-topic peer comparison (median/avg/range + deviation %).
    Matches the logic in backend/routes/analytics.py::get_peer_benchmark.
    """
    peers = db.query(Municipality).filter(Municipality.is_test == False).all()  # noqa: E712
    per_muni: Dict[int, Dict[str, float]] = {}
    for m in peers:
        run = db.query(MonthlyRun).filter(
            MonthlyRun.municipality_id == m.id,
            MonthlyRun.month == month,
        ).first()
        if not run:
            continue
        bucket: Dict[str, float] = {}
        run_lines = db.query(BudgetLine).filter(BudgetLine.run_id == run.id).all()
        for l in run_lines:
            code = l.topic_code or '0'
            bucket[code] = bucket.get(code, 0.0) + float(l.amount or 0.0)
        if bucket:
            per_muni[m.id] = bucket

    peer_ids = [mid for mid in per_muni.keys() if mid != municipality_id]
    peer_count = len(peer_ids)
    if peer_count == 0:
        return {
            'has_peer_data': False,
            'peer_count': 0,
            'outlier_count': 0,
            'by_code': [],
        }

    all_codes = set(my_by_code.keys())
    for mid in peer_ids:
        all_codes.update(per_muni[mid].keys())

    def _median(values: List[float]) -> float:
        if not values:
            return 0.0
        vs = sorted(values)
        n = len(vs)
        mid = n // 2
        return vs[mid] if n % 2 else (vs[mid - 1] + vs[mid]) / 2.0

    rows: List[Dict[str, Any]] = []
    for code in sorted(all_codes):
        peer_vals = [per_muni[mid].get(code, 0.0) for mid in peer_ids]
        peer_nonzero = [v for v in peer_vals if abs(v) > 0.01]
        mine = float(my_by_code.get(code, 0.0))
        if not peer_nonzero and abs(mine) < 0.01:
            continue
        median = round(_median(peer_nonzero), 2)
        if abs(median) > 0.01:
            deviation_pct = round(((mine - median) / abs(median)) * 100, 1)
        else:
            deviation_pct = None
        flag = None
        if deviation_pct is not None:
            if deviation_pct >= 30:
                flag = 'above_peers'
            elif deviation_pct <= -30:
                flag = 'below_peers'
        # Resolve topic name from passed-in code→name map, falling back to code label
        topic_name = (code_names or {}).get(code) or f"קוד {code}"
        rows.append({
            'topic_code': code,
            'topic_name': topic_name,
            'my_amount': round(mine, 2),
            'peer_median': median,
            'peer_avg': round(sum(peer_nonzero) / len(peer_nonzero), 2) if peer_nonzero else 0.0,
            'peer_min': round(min(peer_nonzero), 2) if peer_nonzero else 0.0,
            'peer_max': round(max(peer_nonzero), 2) if peer_nonzero else 0.0,
            'peer_count': len(peer_nonzero),
            'deviation_pct': deviation_pct,
            'flag': flag,
        })
    rows.sort(key=lambda r: -(abs(r['deviation_pct']) if r['deviation_pct'] is not None else 0))
    outliers = sum(1 for r in rows if r['flag'] in ('above_peers', 'below_peers'))
    return {
        'has_peer_data': True,
        'peer_count': peer_count,
        'outlier_count': outliers,
        'by_code': rows,
    }


def _compute_formula_variance(lines, code_names: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Purple-booklet expected vs actual per topic.
    Mirrors backend/routes/analytics.py::get_formula_variance.
    """
    try:
        from backend.routes.positions import CHILD_RATE
    except Exception:
        CHILD_RATE = {'normal': 3820}
    try:
        from backend.data.purple_booklet_rules import BUDGET_TOPIC_RULES
    except Exception:
        BUDGET_TOPIC_RULES = {}

    # Bucket by topic_code
    buckets: Dict[str, Dict[str, Any]] = {}
    for l in lines:
        code = l.topic_code or '0'
        amt = float(l.amount or 0.0)
        b = buckets.setdefault(code, {
            'topic_code': code,
            'topic_name': (code_names or {}).get(code) or (l.budget_topic or f"קוד {code}"),
            'actual_amount': 0.0,
            'actual_regular': 0.0,
            'actual_retro': 0.0,
            'num_children': 0,
        })
        b['actual_amount'] += amt
        if l.is_retro:
            b['actual_retro'] += amt
        else:
            b['actual_regular'] += amt
        if l.num_children:
            b['num_children'] = max(b['num_children'], int(l.num_children))

    rows: List[Dict[str, Any]] = []
    grand_expected = 0.0
    grand_actual_regular = 0.0
    for code, b in buckets.items():
        rule = BUDGET_TOPIC_RULES.get(code) if isinstance(BUDGET_TOPIC_RULES, dict) else None
        rate = None
        basis = 'reported'
        if code == '3':
            rate = CHILD_RATE.get('normal')
        elif rule and isinstance(rule, dict):
            rate = rule.get('rate_per_child')
        kids = b['num_children']
        # NOTE: intentionally do NOT estimate kids from amount/rate — that's
        # tautological (expected ≈ actual ⇒ always 0% variance). If no children
        # data exists we flag the row as 'no_children_data' rather than fake it.
        if rate and kids > 0:
            expected = round(float(rate) * float(kids), 2)
            var_abs = round(b['actual_regular'] - expected, 2)
            var_pct = round(((b['actual_regular'] - expected) / expected) * 100, 1) if expected else None
            if var_pct is None:
                flag = None
            elif abs(var_pct) <= 5:
                flag = 'in_line'
            elif abs(var_pct) <= 15:
                flag = 'material'
            else:
                flag = 'critical'
            grand_expected += expected
            grand_actual_regular += b['actual_regular']
            rows.append({
                'topic_code': code,
                'topic_name': b['topic_name'],
                'num_children': kids,
                'children_basis': basis,
                'rate_per_child': float(rate),
                'expected_amount': expected,
                'actual_regular': round(b['actual_regular'], 2),
                'actual_retro': round(b['actual_retro'], 2),
                'actual_amount': round(b['actual_amount'], 2),
                'variance_abs': var_abs,
                'variance_pct': var_pct,
                'flag': flag,
                'formula': f"{kids} × ₪{float(rate):,.0f} = ₪{expected:,.0f}",
            })
        else:
            # Distinguish "we know the rate but kids are missing" from "no formula at all"
            flag = 'no_children_data' if rate else 'no_formula'
            rows.append({
                'topic_code': code,
                'topic_name': b['topic_name'],
                'num_children': kids or None,
                'children_basis': basis,
                'rate_per_child': float(rate) if rate else None,
                'expected_amount': None,
                'actual_regular': round(b['actual_regular'], 2),
                'actual_retro': round(b['actual_retro'], 2),
                'actual_amount': round(b['actual_amount'], 2),
                'variance_abs': None,
                'variance_pct': None,
                'flag': flag,
                'formula': None,
            })
    rows.sort(key=lambda r: (
        r['variance_pct'] is None,
        -(abs(r['variance_pct']) if r['variance_pct'] is not None else 0),
    ))
    total_var_abs = round(grand_actual_regular - grand_expected, 2)
    total_var_pct = (
        round(((grand_actual_regular - grand_expected) / grand_expected) * 100, 1)
        if grand_expected else None
    )
    material = sum(1 for r in rows if r['flag'] in ('material', 'critical'))
    missing_kids = sum(1 for r in rows if r['flag'] == 'no_children_data')
    no_formula = sum(1 for r in rows if r['flag'] == 'no_formula')
    return {
        'expected_total': round(grand_expected, 2),
        'actual_regular_total': round(grand_actual_regular, 2),
        'variance_abs': total_var_abs,
        'variance_pct': total_var_pct,
        'material_count': material,
        'missing_kids_count': missing_kids,
        'no_formula_count': no_formula,
        'by_code': rows,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Background generation function
# ──────────────────────────────────────────────────────────────────────────────

def _do_generate_monthly(
    job_id: str,
    municipality_id: int,
    month: str,
    generated_by: str,
    db_factory,
):
    """Run in background thread: generate PDF and save DB record."""
    _set_job(job_id, status='running')
    db = next(db_factory())
    try:
        from backend.services.pdf_generator import generate_monthly_report

        muni = db.query(Municipality).filter(Municipality.id == municipality_id).first()
        if not muni:
            _set_job(job_id, status='error', error='הרשות לא נמצאה')
            return

        data = _load_budget_data(municipality_id, month, db)
        if not data:
            _set_job(job_id, status='error', error='אין נתוני תקציב לחודש זה')
            return

        branding = _get_branding_dict(db)

        file_path = generate_monthly_report(
            municipality_id=municipality_id,
            municipality_name=muni.name,
            month=month,
            budget_lines=data['lines'],
            explanations=data['explanations'],
            invoice_total=data['invoice_total'],
            breakdown_total=data['breakdown_total'],
            difference=data['difference'],
            retro_total=data['retro_total'],
            by_code=data['by_code'],
            changes=data['changes'],
            prev_month=data['prev_month'],
            anomalies=data['anomalies'],
            branding=branding,
            tie_out=data.get('tie_out'),
            variance_drivers=data.get('variance_drivers'),
            explained_coverage=data.get('explained_coverage'),
            ytd=data.get('ytd'),
            peer_benchmark=data.get('peer_benchmark'),
            formula_variance=data.get('formula_variance'),
        )

        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        month_heb = _month_display(month)
        file_name = f'דוח_{muni.name}_{month_heb}.pdf'

        report = GeneratedReport(
            municipality_id=municipality_id,
            municipality_name=muni.name,
            month=month,
            report_type='monthly',
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            generated_by=generated_by,
            generated_at=datetime.utcnow(),
            is_auto_generated=(generated_by == 'auto'),
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        _set_job(job_id, status='done', report_id=report.id,
                 download_url=f'/api/reports/download/{report.id}')
        logger.info(f"Report generated: {file_path}")

    except Exception as e:
        # Clean up partial file
        try:
            fname = f"report_{municipality_id}_{month}_monthly.pdf"
            partial = os.path.join('backend', 'reports', str(municipality_id), fname)
            if os.path.exists(partial):
                os.remove(partial)
        except Exception:
            pass
        logger.error(f"Report generation failed for {municipality_id}/{month}: {e}")
        _set_job(job_id, status='error', error=str(e))
    finally:
        db.close()


def _do_generate_comparison(job_id: str, municipality_id: int, generated_by: str, db_factory):
    """Run in background thread: generate comparison PDF."""
    _set_job(job_id, status='running')
    db = next(db_factory())
    try:
        from backend.services.pdf_generator import generate_comparison_report

        muni = db.query(Municipality).filter(Municipality.id == municipality_id).first()
        if not muni:
            _set_job(job_id, status='error', error='הרשות לא נמצאה')
            return

        runs = db.query(MonthlyRun).filter(
            MonthlyRun.municipality_id == municipality_id
        ).order_by(MonthlyRun.month).all()

        runs_as_dicts = [{'month': r.month, 'invoice_total': r.invoice_total or 0,
                          'breakdown_total': r.breakdown_total or 0} for r in runs]

        all_lines: Dict[str, List[Dict]] = {}
        for r in runs:
            lines = db.query(BudgetLine).filter(BudgetLine.run_id == r.id).all()
            all_lines[r.month] = [
                {'topic_code': l.topic_code, 'budget_topic': l.budget_topic,
                 'amount': l.amount, 'is_retro': l.is_retro}
                for l in lines
            ]

        branding = _get_branding_dict(db)

        file_path = generate_comparison_report(
            municipality_id=municipality_id,
            municipality_name=muni.name,
            runs=runs_as_dicts,
            all_lines=all_lines,
            branding=branding,
        )

        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        file_name = f'השוואה_{muni.name}_כל_החודשים.pdf'

        report = GeneratedReport(
            municipality_id=municipality_id,
            municipality_name=muni.name,
            month=None,
            report_type='comparison',
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            generated_by=generated_by,
            generated_at=datetime.utcnow(),
            is_auto_generated=False,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        _set_job(job_id, status='done', report_id=report.id,
                 download_url=f'/api/reports/download/{report.id}')

    except Exception as e:
        logger.error(f"Comparison report failed for {municipality_id}: {e}")
        _set_job(job_id, status='error', error=str(e))
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────────────────────────────────────

class BrandingIn(BaseModel):
    firm_name: Optional[str] = ''
    firm_address: Optional[str] = ''
    firm_phone: Optional[str] = ''
    firm_email: Optional[str] = ''
    primary_color: Optional[str] = '#1E3A5F'
    secondary_color: Optional[str] = '#3B82F6'
    report_footer_text: Optional[str] = ''


class TemplateIn(BaseModel):
    name: str
    description: Optional[str] = ''
    config: Optional[Dict] = {}
    is_default: Optional[bool] = False


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT — List reports for a municipality
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/api/reports/list/{municipality_id}')
async def list_reports(
    municipality_id: int,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if current_user.role == 'municipality' and current_user.municipality_id != municipality_id:
        raise HTTPException(status_code=403, detail='אין הרשאה')

    reports = (
        db.query(GeneratedReport)
        .filter(GeneratedReport.municipality_id == municipality_id)
        .order_by(GeneratedReport.generated_at.desc())
        .all()
    )

    TYPE_DISPLAY = {
        'monthly': 'דוח חודשי',
        'comparison': 'דוח השוואה',
        'custom': 'דוח מותאם',
        'positions': 'דוח משרות',
    }

    result = []
    for r in reports:
        exists = r.file_path and os.path.exists(r.file_path)
        result.append({
            'id': r.id,
            'month': r.month,
            'month_display': _month_display(r.month) if r.month else 'כל החודשים',
            'report_type': r.report_type,
            'report_type_display': TYPE_DISPLAY.get(r.report_type, r.report_type),
            'file_name': r.file_name,
            'file_size': r.file_size,
            'file_size_display': _file_size_display(r.file_size),
            'generated_at': r.generated_at.isoformat() if r.generated_at else None,
            'generated_by': r.generated_by,
            'generated_by_display': 'אוטומטי' if r.is_auto_generated else r.generated_by,
            'download_count': r.download_count,
            'is_auto_generated': r.is_auto_generated,
            'file_exists': exists,
        })

    return result


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT — Download
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/api/reports/download/{report_id}')
async def download_report(
    report_id: int,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    report = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail='הדוח לא נמצא')

    # Access control
    if current_user.role == 'municipality' and current_user.municipality_id != report.municipality_id:
        raise HTTPException(status_code=403, detail='אין הרשאה')

    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(status_code=410, detail='קובץ הדוח לא נמצא — ניתן ליצור מחדש')

    # Increment download count
    report.download_count = (report.download_count or 0) + 1
    db.commit()

    # Build an RFC 5987-compliant Content-Disposition that supports Hebrew
    # filenames. We need: (a) an ASCII fallback that degrades gracefully, and
    # (b) a percent-encoded UTF-8 filename* for modern browsers.
    original_name = report.file_name or 'report.pdf'
    ascii_fallback = f'report_{report.id}.pdf'
    utf8_encoded = _urlquote(original_name, safe='')
    content_disposition = (
        f"attachment; filename=\"{ascii_fallback}\"; "
        f"filename*=UTF-8''{utf8_encoded}"
    )

    return FileResponse(
        path=report.file_path,
        media_type='application/pdf',
        headers={
            'Content-Disposition': content_disposition,
            # Expose so the browser's JS layer can read filename if needed
            'Access-Control-Expose-Headers': 'Content-Disposition',
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT — Generate comparison report
# ──────────────────────────────────────────────────────────────────────────────

@router.post('/api/reports/generate/comparison/{municipality_id}')
async def generate_comparison(
    municipality_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if current_user.role == 'municipality' and current_user.municipality_id != municipality_id:
        raise HTTPException(status_code=403, detail='אין הרשאה')

    job_id = str(uuid.uuid4())
    _set_job(job_id, status='queued', report_id=None, error=None)

    background_tasks.add_task(
        _do_generate_comparison,
        job_id, municipality_id, str(current_user.id), get_db,
    )

    return {'job_id': job_id, 'status': 'queued',
            'status_url': f'/api/reports/status/{job_id}'}


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT — Generate monthly report (on demand)
# ──────────────────────────────────────────────────────────────────────────────

@router.post('/api/reports/generate/{municipality_id}/{month}')
async def generate_report(
    municipality_id: int,
    month: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if current_user.role == 'municipality' and current_user.municipality_id != municipality_id:
        raise HTTPException(status_code=403, detail='אין הרשאה')
    if current_user.role not in ('admin', 'employee', 'municipality'):
        raise HTTPException(status_code=403, detail='אין הרשאה')

    job_id = str(uuid.uuid4())
    _set_job(job_id, status='queued', report_id=None, error=None)

    generated_by = str(current_user.id)

    background_tasks.add_task(
        _do_generate_monthly,
        job_id, municipality_id, month, generated_by, get_db,
    )

    return {'job_id': job_id, 'status': 'queued',
            'status_url': f'/api/reports/status/{job_id}'}


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT — Poll job status
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/api/reports/status/{job_id}')
async def get_job_status(
    job_id: str,
    current_user: User = Depends(require_login),
):
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail='משימה לא נמצאה')

    return job


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT — Delete report
# ──────────────────────────────────────────────────────────────────────────────

@router.delete('/api/reports/{report_id}')
async def delete_report(
    report_id: int,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail='מנהל בלבד')

    report = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail='הדוח לא נמצא')

    # Delete file
    if report.file_path and os.path.exists(report.file_path):
        os.remove(report.file_path)

    db.delete(report)
    db.commit()
    return {'deleted': report_id}


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT — Admin: all reports
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/api/reports/admin/all')
async def admin_all_reports(
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail='מנהל בלבד')

    reports = (
        db.query(GeneratedReport)
        .order_by(GeneratedReport.generated_at.desc())
        .all()
    )

    TYPE_DISPLAY = {
        'monthly': 'דוח חודשי', 'comparison': 'דוח השוואה',
        'custom': 'דוח מותאם', 'positions': 'דוח משרות',
    }

    # Group by municipality
    from collections import defaultdict
    grouped: Dict[int, List] = defaultdict(list)
    muni_names: Dict[int, str] = {}

    for r in reports:
        grouped[r.municipality_id].append({
            'id': r.id,
            'month': r.month,
            'month_display': _month_display(r.month) if r.month else 'כל החודשים',
            'report_type': r.report_type,
            'report_type_display': TYPE_DISPLAY.get(r.report_type, r.report_type),
            'file_name': r.file_name,
            'file_size': r.file_size,
            'file_size_display': _file_size_display(r.file_size),
            'generated_at': r.generated_at.isoformat() if r.generated_at else None,
            'generated_by_display': 'אוטומטי' if r.is_auto_generated else r.generated_by,
            'download_count': r.download_count,
            'file_exists': bool(r.file_path and os.path.exists(r.file_path)),
        })
        muni_names[r.municipality_id] = r.municipality_name

    result = []
    for muni_id, items in grouped.items():
        result.append({
            'municipality_id': muni_id,
            'municipality_name': muni_names.get(muni_id, str(muni_id)),
            'report_count': len(items),
            'reports': items,
        })

    result.sort(key=lambda x: x['municipality_name'])
    return result


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT — Branding GET/POST
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/api/reports/branding')
async def get_branding(
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail='מנהל בלבד')

    brand = db.query(CPABranding).first()
    if not brand:
        return {
            'logo_path': None, 'logo_url': None,
            'firm_name': '', 'firm_address': '', 'firm_phone': '', 'firm_email': '',
            'primary_color': '#1E3A5F', 'secondary_color': '#3B82F6',
            'report_footer_text': '',
        }

    logo_url = None
    if brand.logo_path and os.path.exists(brand.logo_path):
        logo_url = f'/api/reports/branding/logo'

    return {
        'logo_path': brand.logo_path,
        'logo_url': logo_url,
        'firm_name': brand.firm_name,
        'firm_address': brand.firm_address,
        'firm_phone': brand.firm_phone,
        'firm_email': brand.firm_email,
        'primary_color': brand.primary_color,
        'secondary_color': brand.secondary_color,
        'report_footer_text': brand.report_footer_text,
    }


@router.post('/api/reports/branding')
async def save_branding(
    firm_name: str = Form(''),
    firm_address: str = Form(''),
    firm_phone: str = Form(''),
    firm_email: str = Form(''),
    primary_color: str = Form('#1E3A5F'),
    secondary_color: str = Form('#3B82F6'),
    report_footer_text: str = Form(''),
    logo: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail='מנהל בלבד')

    brand = db.query(CPABranding).first()
    if not brand:
        brand = CPABranding()
        db.add(brand)

    brand.firm_name = firm_name
    brand.firm_address = firm_address
    brand.firm_phone = firm_phone
    brand.firm_email = firm_email
    brand.primary_color = primary_color if primary_color.startswith('#') else '#1E3A5F'
    brand.secondary_color = secondary_color if secondary_color.startswith('#') else '#3B82F6'
    brand.report_footer_text = report_footer_text
    brand.updated_by = current_user.id
    brand.updated_at = datetime.utcnow()

    if logo and logo.filename:
        # Validate
        ext = os.path.splitext(logo.filename)[1].lower()
        if ext not in ('.png', '.jpg', '.jpeg', '.svg'):
            raise HTTPException(status_code=400, detail='סוג קובץ לא נתמך. השתמש ב-PNG, JPG, או SVG')

        logo_dir = os.path.join('backend', 'reports', 'logos')
        os.makedirs(logo_dir, exist_ok=True)
        logo_path = os.path.join(logo_dir, f'cpa_logo{ext}')
        content = await logo.read()
        if len(content) > 2 * 1024 * 1024:
            raise HTTPException(status_code=400, detail='הלוגו גדול מדי — מקסימום 2MB')
        with open(logo_path, 'wb') as f:
            f.write(content)
        brand.logo_path = logo_path

    db.commit()
    return {'message': 'הגדרות מיתוג נשמרו בהצלחה'}


@router.get('/api/reports/branding/logo')
async def get_logo(
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    brand = db.query(CPABranding).first()
    if not brand or not brand.logo_path or not os.path.exists(brand.logo_path):
        raise HTTPException(status_code=404, detail='לוגו לא נמצא')

    ext = os.path.splitext(brand.logo_path)[1].lower()
    media_types = {'.png': 'image/png', '.jpg': 'image/jpeg',
                   '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml'}
    return FileResponse(brand.logo_path, media_type=media_types.get(ext, 'image/png'))


@router.delete('/api/reports/branding/logo')
async def delete_logo(
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail='מנהל בלבד')
    brand = db.query(CPABranding).first()
    if brand and brand.logo_path and os.path.exists(brand.logo_path):
        os.remove(brand.logo_path)
    if brand:
        brand.logo_path = None
        db.commit()
    return {'deleted': True}


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT — Templates GET/POST
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/api/reports/templates')
async def get_templates(
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail='מנהל בלבד')

    templates = db.query(ReportTemplate).order_by(ReportTemplate.created_at.desc()).all()
    result = []
    for t in templates:
        try:
            cfg = json.loads(t.config or '{}')
        except Exception:
            cfg = {}
        result.append({
            'id': t.id,
            'name': t.name,
            'description': t.description,
            'config': cfg,
            'is_default': t.is_default,
            'created_at': t.created_at.isoformat() if t.created_at else None,
        })
    return result


@router.post('/api/reports/templates')
async def create_template(
    body: TemplateIn,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail='מנהל בלבד')

    tmpl = ReportTemplate(
        name=body.name,
        description=body.description or '',
        config=json.dumps(body.config or {}),
        created_by=current_user.id,
        is_default=body.is_default or False,
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return {'id': tmpl.id, 'name': tmpl.name, 'message': 'תבנית נשמרה'}


@router.delete('/api/reports/templates/{template_id}')
async def delete_template(
    template_id: int,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail='מנהל בלבד')

    tmpl = db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail='תבנית לא נמצאה')
    db.delete(tmpl)
    db.commit()
    return {'deleted': template_id}
