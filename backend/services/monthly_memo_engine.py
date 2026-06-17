"""
Monthly memo narrative engine.

Core API:
- generate_monthly_memo(period, data, config) -> MemoResult (pure/deterministic)

No side effects in the core function. Sending email remains outside this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models import BudgetLine, MinistryCode, MonthlyRun, Municipality


HEBREW_MONTHS = {
    "01": "ינואר",
    "02": "פברואר",
    "03": "מרץ",
    "04": "אפריל",
    "05": "מאי",
    "06": "יוני",
    "07": "יולי",
    "08": "אוגוסט",
    "09": "ספטמבר",
    "10": "אוקטובר",
    "11": "נובמבר",
    "12": "דצמבר",
}


@dataclass(frozen=True)
class MemoConfig:
    """Configuration surface for narrative and rendering behavior."""

    growth_threshold_pct: float = 5.0
    flat_threshold_pct: float = 2.0
    top_n_movers: int = 5
    material_variance_amount: float = 10000.0
    currency_symbol: str = "₪"
    locale: str = "he-IL"
    timezone: str = "Asia/Jerusalem"
    include_transport_section: bool = True
    include_high_school_section: bool = True
    include_general_section: bool = True


@dataclass(frozen=True)
class MemoMetrics:
    current_total: float
    previous_total: Optional[float]
    change_amount: Optional[float]
    change_pct: Optional[float]
    due_amount: float
    paid_amount: float
    gap_amount: float
    retro_total: float


@dataclass(frozen=True)
class MemoBullet:
    text: str
    amount: Optional[float] = None
    delta: Optional[float] = None


@dataclass(frozen=True)
class MemoSection:
    key: str
    heading: str
    bullets: List[MemoBullet]


@dataclass(frozen=True)
class MemoStructuredContent:
    municipality_name: str
    period: str
    period_display: str
    subject: str
    headline: str
    metrics: MemoMetrics
    sections: List[MemoSection]


@dataclass(frozen=True)
class MemoResult:
    structured: MemoStructuredContent
    html: str
    text: str


def _month_display(period: str) -> str:
    if period and len(period) >= 7 and period[4] == "-":
        year, mon = period[:4], period[5:7]
        return f"{HEBREW_MONTHS.get(mon, mon)} {year}"
    return period or "—"


def _mm_yyyy(period: str) -> str:
    if period and len(period) >= 7 and period[4] == "-":
        return f"{period[5:7]}/{period[:4]}"
    return period or "—"


def _money(value: Optional[float], symbol: str = "₪") -> str:
    if value is None:
        return f"{symbol}0"
    return f"{symbol}{int(round(float(value))):,}"


def _pct(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{value:+.1f}%"


def _safe_ratio_pct(current: float, previous: float) -> Optional[float]:
    if abs(previous) < 1e-9:
        return None
    return ((current - previous) / abs(previous)) * 100.0


def _normalize_line(line: Dict[str, Any]) -> Dict[str, Any]:
    code = str(line.get("topic_code") or "").strip()
    name = str(line.get("budget_topic") or line.get("topic_name") or f"קוד {code}").strip()
    amount = float(line.get("amount") or 0.0)
    period_month = str(line.get("period_month") or "").strip()
    is_retro = bool(line.get("is_retro") or str(line.get("line_type") or "") == "retro")
    return {
        "topic_code": code,
        "budget_topic": name,
        "amount": amount,
        "period_month": period_month,
        "is_retro": is_retro,
    }


def _aggregate_by_code(lines: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_code: Dict[str, Dict[str, Any]] = {}
    for src in lines:
        line = _normalize_line(src)
        code = line["topic_code"]
        if code not in by_code:
            by_code[code] = {
                "code": code,
                "name": line["budget_topic"] or f"קוד {code}",
                "amount": 0.0,
                "retro_months": set(),
                "has_retro": False,
            }
        by_code[code]["amount"] += line["amount"]
        if line["is_retro"] and line["period_month"]:
            by_code[code]["retro_months"].add(line["period_month"])
            by_code[code]["has_retro"] = True
    return by_code


def _section_key(code: str, name: str, code_metadata: Dict[str, Dict[str, Any]]) -> str:
    meta = code_metadata.get(code, {})
    category = str(meta.get("category") or "").strip()
    if "גן" in category or code in {"3", "19", "33"}:
        return "kindergarten"
    if "הסע" in category or code == "50":
        return "transport"
    if "תיכון" in category or "תיכון" in name:
        return "high_school"
    return "general"


def _headline_from_change(change_pct: Optional[float], cfg: MemoConfig) -> str:
    if change_pct is None:
        return "אין נתוני השוואה לחודש קודם, לכן מוצג סיכום חודשי ללא מגמה."
    if change_pct >= cfg.growth_threshold_pct:
        return f"התקבולים עלו ביחס לחודש קודם ({_pct(change_pct)})."
    if change_pct <= -cfg.growth_threshold_pct:
        return f"התקבולים ירדו ביחס לחודש קודם ({_pct(change_pct)})."
    if abs(change_pct) <= cfg.flat_threshold_pct:
        return f"התקבולים נותרו יציבים יחסית לחודש קודם ({_pct(change_pct)})."
    return f"נרשם שינוי מתון ביחס לחודש קודם ({_pct(change_pct)})."


def _build_sections(
    movers: List[Dict[str, Any]],
    cfg: MemoConfig,
    code_metadata: Dict[str, Dict[str, Any]],
) -> List[MemoSection]:
    grouped: Dict[str, List[MemoBullet]] = {
        "kindergarten": [],
        "transport": [],
        "high_school": [],
        "general": [],
    }

    for m in movers:
        retro_note = ""
        retro_months = sorted(m.get("retro_months") or [])
        if retro_months:
            retro_note = f" (כולל רטרו עבור {', '.join(_mm_yyyy(x) for x in retro_months)})"
        txt = (
            f"{m['name']} (קוד {m['code']}) — שינוי { _money(m['delta']) } "
            f"לעומת חודש קודם{retro_note}"
        )
        grouped[m["section"]].append(MemoBullet(text=txt, amount=m["current"], delta=m["delta"]))

    ordered = [
        ("kindergarten", "1. גנים", True),
        ("transport", "2. הסעות", cfg.include_transport_section),
        ("high_school", "3. תיכון", cfg.include_high_school_section),
        ("general", "4. כללי", cfg.include_general_section),
    ]

    sections: List[MemoSection] = []
    for key, heading, enabled in ordered:
        if not enabled:
            continue
        bullets = grouped[key] or [MemoBullet(text="לא זוהו שינויים מהותיים בחודש זה.")]
        sections.append(MemoSection(key=key, heading=heading, bullets=bullets))
    return sections


def _render_html(content: MemoStructuredContent, cfg: MemoConfig) -> str:
    esc = escape
    rows = []
    for sec in content.sections:
        rows.append(
            f'<tr><td style="padding:14px 20px 6px 20px;font-family:Arial,sans-serif;font-size:18px;font-weight:700;color:#1f2937;">{esc(sec.heading)}</td></tr>'
        )
        for b in sec.bullets:
            rows.append(
                "<tr><td style=\"padding:2px 20px 8px 20px;font-family:Arial,sans-serif;font-size:15px;color:#374151;line-height:1.6;\">"
                f"• {esc(b.text)}"
                "</td></tr>"
            )

    html = (
        '<div dir="rtl" style="direction:rtl;text-align:right;max-width:600px;margin:0 auto;">'
        '<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" '
        'style="max-width:600px;border:1px solid #e5e7eb;border-radius:10px;background:#ffffff;">'
        '<tbody>'
        '<tr><td style="padding:18px 20px 8px 20px;font-family:Arial,sans-serif;font-size:16px;color:#111827;">מכובדי שלום רב,</td></tr>'
        f'<tr><td style="padding:0 20px 12px 20px;font-family:Arial,sans-serif;font-size:16px;color:#111827;">להלן ניתוח מית"ר לחודש {esc(content.period_display)}</td></tr>'
        f'<tr><td style="padding:0 20px 14px 20px;font-family:Arial,sans-serif;font-size:15px;color:#374151;">{esc(content.headline)}</td></tr>'
        '<tr><td style="padding:0 20px 12px 20px;">'
        '<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="border-collapse:collapse;">'
        '<tbody>'
        f'<tr><td style="padding:4px 0;font-family:Arial,sans-serif;font-size:14px;color:#6b7280;">סה"כ לחודש:</td><td style="padding:4px 0;font-family:Arial,sans-serif;font-size:14px;color:#111827;font-weight:700;">{esc(_money(content.metrics.current_total, cfg.currency_symbol))}</td></tr>'
        f'<tr><td style="padding:4px 0;font-family:Arial,sans-serif;font-size:14px;color:#6b7280;">מגיע:</td><td style="padding:4px 0;font-family:Arial,sans-serif;font-size:14px;color:#111827;">{esc(_money(content.metrics.due_amount, cfg.currency_symbol))}</td></tr>'
        f'<tr><td style="padding:4px 0;font-family:Arial,sans-serif;font-size:14px;color:#6b7280;">שולם:</td><td style="padding:4px 0;font-family:Arial,sans-serif;font-size:14px;color:#111827;">{esc(_money(content.metrics.paid_amount, cfg.currency_symbol))}</td></tr>'
        f'<tr><td style="padding:4px 0;font-family:Arial,sans-serif;font-size:14px;color:#6b7280;">פער:</td><td style="padding:4px 0;font-family:Arial,sans-serif;font-size:14px;color:#111827;">{esc(_money(content.metrics.gap_amount, cfg.currency_symbol))}</td></tr>'
        '</tbody></table></td></tr>'
        + "".join(rows)
        + '<tr><td style="padding:16px 20px 6px 20px;font-family:Arial,sans-serif;font-size:15px;color:#111827;">בכבוד רב,</td></tr>'
        f'<tr><td style="padding:0 20px 2px 20px;font-family:Arial,sans-serif;font-size:15px;color:#111827;">{esc(content.municipality_name)} — צוות הבקרה</td></tr>'
        '<tr><td style="padding:0 20px 20px 20px;font-family:Arial,sans-serif;font-size:12px;color:#6b7280;">מזכר חודשי אוטומטי</td></tr>'
        '</tbody></table></div>'
    )
    return html


def _render_text(content: MemoStructuredContent, cfg: MemoConfig) -> str:
    lines: List[str] = [
        "מכובדי שלום רב,",
        f"להלן ניתוח מית\"ר לחודש {content.period_display}",
        content.headline,
        "",
        f"סה\"כ לחודש: {_money(content.metrics.current_total, cfg.currency_symbol)}",
        f"מגיע: {_money(content.metrics.due_amount, cfg.currency_symbol)}",
        f"שולם: {_money(content.metrics.paid_amount, cfg.currency_symbol)}",
        f"פער: {_money(content.metrics.gap_amount, cfg.currency_symbol)}",
        "",
    ]

    for sec in content.sections:
        lines.append(sec.heading)
        for b in sec.bullets:
            lines.append(f"- {b.text}")
        lines.append("")

    lines.append("בכבוד רב,")
    lines.append(f"{content.municipality_name} — צוות הבקרה")
    return "\n".join(lines).strip()


def generate_monthly_memo(
    period: str,
    data: Dict[str, Any],
    config: Optional[MemoConfig] = None,
) -> MemoResult:
    """Pure deterministic monthly memo generator."""
    cfg = config or MemoConfig()

    municipality_name = str(data.get("municipality_name") or "רשות מקומית").strip()
    current_lines = [_normalize_line(x) for x in (data.get("current_lines") or [])]
    previous_lines = [_normalize_line(x) for x in (data.get("previous_lines") or [])]
    code_metadata = data.get("code_metadata") or {}

    current_total = float(sum(x["amount"] for x in current_lines))
    previous_total = float(sum(x["amount"] for x in previous_lines)) if previous_lines else None
    change_amount = (current_total - previous_total) if previous_total is not None else None
    change_pct = _safe_ratio_pct(current_total, previous_total) if previous_total is not None else None

    due_amount = float(data.get("due_amount", data.get("breakdown_total", 0.0)) or 0.0)
    paid_amount = float(data.get("paid_amount", data.get("invoice_total", 0.0)) or 0.0)
    gap_amount = float(data.get("gap_amount", (due_amount - paid_amount)))
    retro_total = float(sum(x["amount"] for x in current_lines if x.get("is_retro")))

    current_by_code = _aggregate_by_code(current_lines)
    previous_by_code = _aggregate_by_code(previous_lines)

    movers: List[Dict[str, Any]] = []
    all_codes = sorted(set(current_by_code.keys()) | set(previous_by_code.keys()))
    for code in all_codes:
        cur = current_by_code.get(code, {})
        prv = previous_by_code.get(code, {})
        cur_amount = float(cur.get("amount", 0.0))
        prev_amount = float(prv.get("amount", 0.0))
        delta = cur_amount - prev_amount
        if abs(delta) < cfg.material_variance_amount:
            continue
        name = str(cur.get("name") or prv.get("name") or f"קוד {code}")
        section = _section_key(code, name, code_metadata)
        movers.append(
            {
                "code": code,
                "name": name,
                "current": cur_amount,
                "previous": prev_amount,
                "delta": delta,
                "retro_months": sorted(cur.get("retro_months", set())),
                "section": section,
            }
        )

    movers.sort(key=lambda m: abs(m["delta"]), reverse=True)
    movers = movers[: cfg.top_n_movers]

    sections = _build_sections(movers, cfg, code_metadata)
    period_display = _month_display(period)
    headline = _headline_from_change(change_pct, cfg)

    structured = MemoStructuredContent(
        municipality_name=municipality_name,
        period=period,
        period_display=period_display,
        subject=f"ניתוח מית\"ר לחודש {period_display} - {municipality_name}",
        headline=headline,
        metrics=MemoMetrics(
            current_total=current_total,
            previous_total=previous_total,
            change_amount=change_amount,
            change_pct=change_pct,
            due_amount=due_amount,
            paid_amount=paid_amount,
            gap_amount=gap_amount,
            retro_total=retro_total,
        ),
        sections=sections,
    )

    html = _render_html(structured, cfg)
    text = _render_text(structured, cfg)
    return MemoResult(structured=structured, html=html, text=text)


def build_monthly_memo_data_bundle(
    db: Session,
    municipality_id: int,
    period: str,
) -> Dict[str, Any]:
    """Load memo data via existing repository/ORM layer (separate from pure generator)."""
    municipality = db.query(Municipality).filter(Municipality.id == municipality_id).first()
    if not municipality:
        raise ValueError(f"Municipality {municipality_id} not found")

    current_run = (
        db.query(MonthlyRun)
        .filter(
            MonthlyRun.municipality_id == municipality_id,
            MonthlyRun.month == period,
        )
        .first()
    )

    current_lines: List[Dict[str, Any]] = []
    if current_run:
        lines = db.query(BudgetLine).filter(BudgetLine.run_id == current_run.id).all()
        current_lines = [
            {
                "topic_code": l.topic_code,
                "budget_topic": l.budget_topic,
                "amount": float(l.amount or 0.0),
                "period_month": l.period_month,
                "is_retro": bool(l.is_retro),
                "line_type": l.line_type,
            }
            for l in lines
        ]

    prev_run = (
        db.query(MonthlyRun)
        .filter(
            MonthlyRun.municipality_id == municipality_id,
            MonthlyRun.month < period,
        )
        .order_by(MonthlyRun.month.desc())
        .first()
    )

    previous_lines: List[Dict[str, Any]] = []
    if prev_run:
        lines = db.query(BudgetLine).filter(BudgetLine.run_id == prev_run.id).all()
        previous_lines = [
            {
                "topic_code": l.topic_code,
                "budget_topic": l.budget_topic,
                "amount": float(l.amount or 0.0),
                "period_month": l.period_month,
                "is_retro": bool(l.is_retro),
                "line_type": l.line_type,
            }
            for l in lines
        ]

    code_rows = db.query(MinistryCode).filter(MinistryCode.is_active == True).all()
    code_metadata = {
        str(r.code): {
            "name_short": r.name_short,
            "category": r.category,
        }
        for r in code_rows
    }

    due_amount = float(current_run.breakdown_total or 0.0) if current_run else 0.0
    paid_amount = float(current_run.invoice_total or 0.0) if current_run else 0.0

    return {
        "municipality_name": str(municipality.name),
        "current_lines": current_lines,
        "previous_lines": previous_lines,
        "due_amount": due_amount,
        "paid_amount": paid_amount,
        "gap_amount": due_amount - paid_amount,
        "code_metadata": code_metadata,
    }
