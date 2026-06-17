"""
Positions & Quotas Analysis (משרות ותקנים)

GET /api/positions/analysis/{municipality_id}/{month}

Calculates position entitlements vs. current allocations for:
  A. עוזרות גננות (code 19) — kindergarten assistants
  B. גן ילדים נוסף (code 3)  — additional kindergartens
  C. ילדי השלמה (code 3)     — completion children
  D. יום 6 — 6-day week bonus
  E. קצין ביקור סדיר (code 5/45) — attendance officer

Per the Ministry of Education Purple Booklet (חוברת התקצוב).
"""

import math
import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.models.budget_line import BudgetLine
from backend.models.municipality import Municipality
from backend.models.user import User
from backend.utils.auth_guards import require_login

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/positions", tags=["positions"])

# ──────────────────────────────────────────────────────────
# Ministry constants (Purple Booklet)
# ──────────────────────────────────────────────────────────
DIVISOR_WITH_GRANT = 31      # ילדים לגן — מקבל מענק איזון
DIVISOR_WITHOUT_GRANT = 33   # ילדים לגן — לא מקבל מענק
MIN_CHILDREN_FOR_SECOND_KG = 46   # threshold for additional kindergarten
COMPLETION_CHILDREN_TARGET = 28   # minimum children for full group
SIX_DAY_BONUS_RATE = 0.1785       # 17.85% bonus for 6-day week
ATTENDANCE_OFFICER_CHILD_RATIO = 500  # one officer per 500 children
OFFICER_PARTICIPATION_PCT = 0.75  # ministry pays 75%

# Per-child monthly budget rates (NIS) — estimated from Purple Booklet p.45
CHILD_RATE = {
    "normal": 3820,       # גיל 3-4 regular
    "special_hard": 8360, # חנמ קשה
    "special_easy": 4025, # חנמ קל
    "completion": 3820,   # ילדי השלמה
}

# Estimated annual officer salary (NIS)
ESTIMATED_OFFICER_ANNUAL = 120_000


# ──────────────────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────────────────
class FormulaParts(BaseModel):
    total_children: Optional[int] = None
    divisor: Optional[int] = None
    kindergartens: Optional[float] = None
    positions: Optional[float] = None
    formula_text: str = ""


class PositionItem(BaseModel):
    id: str
    type: str
    code: str
    icon: str
    current: int
    entitled: int
    gap: int
    gap_direction: str           # "missing" | "surplus" | "ok"
    status: str
    severity: str                # "critical" | "attention" | "ok" | "surplus" | "none"
    annual_gap_value: float
    monthly_gap_value: float
    formula_parts: FormulaParts
    what_to_do: List[str]
    ministry_reference: str
    email_subject: str
    email_body: str
    extra: Dict[str, Any] = {}   # extra data for special cards


class Summary(BaseModel):
    total_positions_analyzed: int
    positions_ok: int
    positions_missing: int
    positions_surplus: int
    total_potential_value: float
    urgent_count: int


class PositionsAnalysisResponse(BaseModel):
    municipality_id: int
    municipality_name: str
    month: str
    grant_status: str
    divisor: int
    total_children: int
    summary: Summary
    positions: List[PositionItem]
    has_data: bool


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────
def _estimate_children(budget_topic: str, amount: float) -> int:
    """Estimate number of children from a budget line amount."""
    t = (budget_topic or "").lower()
    if "קשה" in t:
        rate = CHILD_RATE["special_hard"]
    elif "קל" in t:
        rate = CHILD_RATE["special_easy"]
    elif "השלמה" in t:
        rate = CHILD_RATE["completion"]
    else:
        rate = CHILD_RATE["normal"]
    if rate <= 0 or amount <= 0:
        return 0
    return max(0, round(amount / rate))


def _fmt(amount: float) -> str:
    """Format NIS amount with comma separator."""
    return f"₪{amount:,.0f}"


def _gap_status(gap: int) -> tuple:
    """Return (status_text, severity, gap_direction) from gap value."""
    if gap > 3:
        return "חוסר משמעותי", "critical", "missing"
    if gap > 0:
        return "חסר", "attention", "missing"
    if gap == 0:
        return "תקין", "ok", "ok"
    return "עודף", "surplus", "surplus"


def _build_email(subject: str, body: str):
    return subject, body


# ──────────────────────────────────────────────────────────
# Core analysis functions
# ──────────────────────────────────────────────────────────
def _analyze_assistants(
    code19_lines: List[BudgetLine],
    code3_lines: List[BudgetLine],
    total_children: int,
    divisor: int,
    municipality_name: str,
    month: str,
) -> PositionItem:
    """CALCULATION A — עוזרות גננות (code 19)."""
    current = len(code19_lines)

    if total_children > 0:
        kindergartens_entitled = total_children / divisor
        positions_entitled = math.ceil(kindergartens_entitled)
    else:
        kindergartens_entitled = len([l for l in code3_lines if "גיל" in (l.budget_topic or "") or "ח\"מ" not in (l.budget_topic or "")]) or current
        positions_entitled = current  # no children data → no change
        kindergartens_entitled = float(positions_entitled)

    gap = positions_entitled - current
    status, severity, direction = _gap_status(gap)

    # Cost per position: average of code 19 amounts
    avg_monthly = (
        sum(l.amount for l in code19_lines) / len(code19_lines)
        if code19_lines else 9_000
    )
    annual_gap_value = abs(gap) * avg_monthly * 12
    monthly_gap_value = abs(gap) * avg_monthly

    formula_text = (
        f"{total_children} ÷ [{divisor}] = {kindergartens_entitled:.2f} גנים "
        f"× 1 עוזרת לגן = {kindergartens_entitled:.2f} משרות → עיגול: {positions_entitled}"
    )

    subject = f"בקשה לתקן עוזרות גננות — {municipality_name}"
    body = (
        f"שלום,\n"
        f"בבדיקת נתוני {month} עלה כי הרשות זכאית ל-{gap} משרות עוזרות נוספות.\n"
        f"מצ\"ב נתונים:\n"
        f"• ילדים מתוקצבים: {total_children}\n"
        f"• קבוע חישוב: {divisor} ילדים לגן\n"
        f"• משרות מגיעות: {positions_entitled}\n"
        f"• משרות קיימות: {current}\n"
        f"• הפרש: {gap} משרות\n\n"
        f"נבקש טיפולכם בהגדלת התקן.\nתודה"
    )

    return PositionItem(
        id="assistants",
        type="עוזרות גננות",
        code="19",
        icon="👩‍🏫",
        current=current,
        entitled=positions_entitled,
        gap=gap,
        gap_direction=direction,
        status=status,
        severity=severity,
        annual_gap_value=round(annual_gap_value),
        monthly_gap_value=round(monthly_gap_value),
        formula_parts=FormulaParts(
            total_children=total_children,
            divisor=divisor,
            kindergartens=round(kindergartens_entitled, 2),
            positions=round(kindergartens_entitled, 2),
            formula_text=formula_text,
        ),
        what_to_do=[
            "הגש בקשה לאגף בכיר אמח'י",
            "המועד האחרון: 31 ביולי",
            "צרף: רשימת ילדים מעודכנת + אישור בטיחות גן",
        ],
        ministry_reference="חוברת התקצוב עמ' 48",
        email_subject=subject,
        email_body=body,
    )


def _analyze_kindergartens(
    code3_lines: List[BudgetLine],
    total_children: int,
    municipality_name: str,
    month: str,
) -> PositionItem:
    """CALCULATION B — גן ילדים נוסף (code 3)."""
    # Count only "main" kindergarten lines (exclude completion / special)
    main_lines = [
        l for l in code3_lines
        if "גיל" in (l.budget_topic or "") or (
            "ח\"מ" not in (l.budget_topic or "") and "השלמה" not in (l.budget_topic or "")
        )
    ]
    current_kg = len(main_lines) or len(code3_lines)
    avg_kg_monthly = (
        sum(l.amount for l in main_lines) / len(main_lines)
        if main_lines else (
            sum(l.amount for l in code3_lines) / len(code3_lines)
            if code3_lines else 26_000
        )
    )

    if total_children > 0 and current_kg > 0:
        children_per_kg = total_children / current_kg
    else:
        children_per_kg = 0

    gap = 0
    entitled = current_kg
    gap_to_next = 0
    severity = "none"
    status_text = "תקין"
    gap_direction = "ok"
    annual_gap_value = 0.0

    if children_per_kg > 35:
        gap_to_next = max(0, MIN_CHILDREN_FOR_SECOND_KG - total_children)
        if gap_to_next <= 0:
            # Already entitled to additional kindergarten
            gap = 1
            entitled = current_kg + 1
            status_text = "זכאי לגן נוסף"
            severity = "attention"
            gap_direction = "missing"
            annual_gap_value = avg_kg_monthly * 12
        else:
            status_text = f"חסרים {gap_to_next} ילדים לגן נוסף"
            severity = "attention"
            gap_direction = "missing"

    formula_text = (
        f"{total_children} ילדים ÷ {current_kg} גנים = {children_per_kg:.1f} ילדים לגן"
        + (f" → נדרש גן נוסף מ-{MIN_CHILDREN_FOR_SECOND_KG} ילדים" if children_per_kg > 35 else "")
    )

    subject = f"בקשה לתקן גן ילדים נוסף — {municipality_name}"
    body = (
        f"שלום,\n"
        f"בבדיקת נתוני {month} עלה כי ייתכן זכאות לגן ילדים נוסף.\n"
        f"• סך ילדים: {total_children}\n"
        f"• גנים קיימים: {current_kg}\n"
        f"• ממוצע ילדים לגן: {children_per_kg:.1f}\n"
        f"נבקש בחינת הזכאות לגן נוסף.\nתודה"
    )

    return PositionItem(
        id="kindergartens",
        type="גן ילדים נוסף",
        code="3",
        icon="🏫",
        current=current_kg,
        entitled=entitled,
        gap=gap,
        gap_direction=gap_direction,
        status=status_text,
        severity=severity,
        annual_gap_value=round(annual_gap_value),
        monthly_gap_value=round(annual_gap_value / 12),
        formula_parts=FormulaParts(
            total_children=total_children,
            formula_text=formula_text,
        ),
        what_to_do=[
            "פנה למחוז לבדיקת תקן גן נוסף",
            f"נדרשים לפחות {MIN_CHILDREN_FOR_SECOND_KG} ילדים לאישור",
            "הגש בקשה עד סוף אפריל",
        ],
        ministry_reference="חוברת התקצוב עמ' 46",
        email_subject=subject,
        email_body=body,
        extra={"children_per_kg": round(children_per_kg, 1), "gap_to_next": gap_to_next},
    )


def _analyze_completion_children(
    code3_lines: List[BudgetLine],
    municipality_name: str,
    month: str,
) -> PositionItem:
    """CALCULATION C — ילדי השלמה (code 3)."""
    # completion lines are those explicitly labeled
    completion_lines = [
        l for l in code3_lines if "השלמה" in (l.budget_topic or "")
    ]

    # Estimate how many children are in each main group
    main_lines = [
        l for l in code3_lines
        if "גיל" in (l.budget_topic or "")
    ]
    current_receiving = len(completion_lines)

    # Count groups with fewer than 28 children
    potential_groups = 0
    potential_children = 0
    for line in main_lines:
        estimated = _estimate_children(line.budget_topic, line.amount)
        if estimated < COMPLETION_CHILDREN_TARGET:
            potential_groups += 1
            potential_children += COMPLETION_CHILDREN_TARGET - estimated

    # Rough value: each completion child ≈ rate / 12 * 12 = rate per year
    cost_per_child_annual = CHILD_RATE["completion"]
    potential_value = potential_children * cost_per_child_annual

    gap = potential_groups - current_receiving
    if potential_groups > 0 and current_receiving == 0:
        status_text = "לא מנוצל"
        severity = "attention"
        gap_direction = "missing"
    elif potential_groups > current_receiving:
        status_text = "חסר"
        severity = "attention"
        gap_direction = "missing"
    elif potential_groups == 0 and current_receiving == 0:
        status_text = "לא רלוונטי"
        severity = "none"
        gap_direction = "ok"
        gap = 0
    else:
        status_text = "תקין"
        severity = "ok"
        gap_direction = "ok"
        gap = 0

    formula_text = (
        f"{len(main_lines)} גנים ראשיים — {potential_groups} גנים עם פחות מ-{COMPLETION_CHILDREN_TARGET} ילדים"
        f" → {potential_children} ילדי השלמה אפשריים"
    )

    subject = f"בקשה לתקן ילדי השלמה — {municipality_name}"
    body = (
        f"שלום,\n"
        f"בבדיקת נתוני {month} עלה כי קיימת אפשרות לרישום ילדי השלמה.\n"
        f"• גנים עם פחות מ-{COMPLETION_CHILDREN_TARGET} ילדים: {potential_groups}\n"
        f"• ילדי השלמה אפשריים: {potential_children}\n"
        f"נבקש בדיקת הזכאות ורישום ילדי השלמה.\nתודה"
    )

    return PositionItem(
        id="completion_children",
        type="ילדי השלמה",
        code="3",
        icon="👶",
        current=current_receiving,
        entitled=potential_groups,
        gap=max(0, gap),
        gap_direction=gap_direction,
        status=status_text,
        severity=severity,
        annual_gap_value=round(potential_value),
        monthly_gap_value=round(potential_value / 12),
        formula_parts=FormulaParts(
            total_children=potential_children,
            formula_text=formula_text,
        ),
        what_to_do=[
            f"בגנים עם פחות מ-{COMPLETION_CHILDREN_TARGET} ילדים — הגש בקשה לילדי השלמה",
            "המועד האחרון: 31 בדצמבר",
            "הגש דרך מערכת גני ילדים — ילדי השלמה",
        ],
        ministry_reference="חוברת התקצוב עמ' 47",
        email_subject=subject,
        email_body=body,
        extra={"potential_groups": potential_groups, "potential_children": potential_children},
    )


def _analyze_six_day(
    code19_lines: List[BudgetLine],
    municipality_name: str,
    month: str,
) -> PositionItem:
    """CALCULATION D — יום 6 (6-day week bonus)."""
    # Check if any code 19 line already has the 6-day marker (17.85% bonus)
    total_code19_amount = sum(l.amount for l in code19_lines)
    # A simple heuristic: look for much higher amounts that suggest 6-day bonus
    avg_amount = total_code19_amount / len(code19_lines) if code19_lines else 0
    # Lines with >10% above average might indicate 6-day bonus
    high_lines = [l for l in code19_lines if l.amount > avg_amount * 1.10]
    already_using = len(high_lines) > 0 and len(high_lines) < len(code19_lines)

    if already_using:
        status_text = "מנוצל חלקית"
        severity = "routine"
        gap_direction = "missing"
        gap = 1
        bonus_annual = total_code19_amount * SIX_DAY_BONUS_RATE * 12
    elif not code19_lines:
        status_text = "לא רלוונטי"
        severity = "none"
        gap_direction = "ok"
        gap = 0
        bonus_annual = 0.0
    else:
        status_text = "לא מנוצל — אפשרי +17.85%"
        severity = "routine"
        gap_direction = "missing"
        gap = 1
        bonus_annual = total_code19_amount * SIX_DAY_BONUS_RATE * 12

    formula_text = (
        f"עלות עוזרות חודשית: {_fmt(total_code19_amount)} "
        f"× 17.85% = {_fmt(total_code19_amount * SIX_DAY_BONUS_RATE)} תוספת לחודש"
    )

    subject = f"תוספת גן 6 ימים — {municipality_name}"
    body = (
        f"שלום,\n"
        f"בבדיקת נתוני {month} עלה כי ייתכן זכאות לתוספת גן 6 ימים (17.85%).\n"
        f"אם גן פועל 6 ימים בשבוע, ניתן לקבל תוספת של 17.85% על עלות העוזרת.\n"
        f"נבקש בדיקת הזכאות.\nתודה"
    )

    return PositionItem(
        id="six_day",
        type="גן 6 ימים",
        code="19",
        icon="📅",
        current=1 if already_using else 0,
        entitled=1,
        gap=gap,
        gap_direction=gap_direction,
        status=status_text,
        severity=severity,
        annual_gap_value=round(bonus_annual),
        monthly_gap_value=round(bonus_annual / 12),
        formula_parts=FormulaParts(
            formula_text=formula_text,
        ),
        what_to_do=[
            "אם גן פועל 6 ימים — דווח למשרד החינוך",
            "תקבל תוספת 17.85% על עלות העוזרת",
            "יש לצרף אישור מנהל/ת הגן",
        ],
        ministry_reference="חוברת התקצוב עמ' 48",
        email_subject=subject,
        email_body=body,
    )


def _analyze_attendance_officer(
    officer_lines: List[BudgetLine],
    total_children: int,
    municipality_name: str,
    month: str,
) -> PositionItem:
    """CALCULATION E — קצין ביקור סדיר (code 45 / code 5)."""
    current = len(officer_lines)
    entitled = max(1, math.ceil(total_children / ATTENDANCE_OFFICER_CHILD_RATIO)) if total_children > 0 else 1
    gap = entitled - current

    if current == 0:
        status_text = "לא מתוקצב — בדוק זכאות"
        severity = "attention"
        gap_direction = "missing"
    elif gap > 0:
        status_text = "חסר"
        severity = "attention"
        gap_direction = "missing"
    elif gap < 0:
        status_text = "עודף"
        severity = "surplus"
        gap_direction = "surplus"
    else:
        status_text = "תקין"
        severity = "ok"
        gap_direction = "ok"

    ministry_share = ESTIMATED_OFFICER_ANNUAL * OFFICER_PARTICIPATION_PCT
    annual_gap_value = abs(gap) * ministry_share if gap > 0 else 0.0

    formula_text = (
        f"{total_children} ילדים ÷ {ATTENDANCE_OFFICER_CHILD_RATIO} = {entitled} קב'סים מגיעים"
        if total_children > 0
        else "קצין ביקור סדיר — נדרש בדיקת זכאות"
    )

    subject = f"בקשה לתקן קצין ביקור סדיר — {municipality_name}"
    body = (
        f"שלום,\n"
        f"בבדיקת נתוני {month} עלה כי הרשות {'אינה מתוקצבת' if current == 0 else 'חסרה תקן'} לקצין ביקור סדיר.\n"
        f"• ילדים מתוקצבים: {total_children}\n"
        f"• קב'סים מגיעים: {entitled}\n"
        f"• קב'סים קיימים: {current}\n"
        f"משרד החינוך משתתף ב-75% מעלות המשרה.\n"
        f"נבקש בדיקת הזכאות.\nתודה"
    )

    return PositionItem(
        id="attendance_officer",
        type="קצין ביקור סדיר",
        code="45",
        icon="👮",
        current=current,
        entitled=entitled,
        gap=gap,
        gap_direction=gap_direction,
        status=status_text,
        severity=severity,
        annual_gap_value=round(annual_gap_value),
        monthly_gap_value=round(annual_gap_value / 12),
        formula_parts=FormulaParts(
            total_children=total_children,
            formula_text=formula_text,
        ),
        what_to_do=[
            "בדוק זכאות לקצין ביקור סדיר",
            "משרד החינוך משתתף ב-75% מהעלות",
            "פנה למחוז לאישור תקן",
        ],
        ministry_reference="חוברת התקצוב עמ' 10",
        email_subject=subject,
        email_body=body,
    )


# ──────────────────────────────────────────────────────────
# Shared calculation engine (used by both endpoints)
# ──────────────────────────────────────────────────────────
def calculate_positions_for_municipality(
    municipality: Municipality,
    month: str,
    db: Session,
) -> PositionsAnalysisResponse:
    """
    Core logic: load budget lines and run all 5 position analyses.
    Shared by the municipality endpoint and the admin summary endpoint.
    """
    all_lines = (
        db.query(BudgetLine)
        .filter(
            BudgetLine.municipality_id == municipality.id,
            BudgetLine.period_month == month,
        )
        .all()
    )

    if not all_lines:
        all_lines = (
            db.query(BudgetLine)
            .filter(
                BudgetLine.municipality_id == municipality.id,
                BudgetLine.current_month == month,
            )
            .all()
        )

    code3_lines = [l for l in all_lines if l.topic_code == "3"]
    code19_lines = [l for l in all_lines if l.topic_code == "19"]
    code33_lines = [l for l in all_lines if l.topic_code == "33"]
    officer_lines = [l for l in all_lines if l.topic_code in ("45", "5")]

    has_data = bool(code3_lines or code19_lines or code33_lines)

    if not has_data:
        return PositionsAnalysisResponse(
            municipality_id=municipality.id,
            municipality_name=municipality.name,
            month=month,
            grant_status="לא ידוע",
            divisor=DIVISOR_WITHOUT_GRANT,
            total_children=0,
            summary=Summary(
                total_positions_analyzed=0,
                positions_ok=0,
                positions_missing=0,
                positions_surplus=0,
                total_potential_value=0,
                urgent_count=0,
            ),
            positions=[],
            has_data=False,
        )

    has_grant = len(code33_lines) > 0
    divisor = DIVISOR_WITH_GRANT if has_grant else DIVISOR_WITHOUT_GRANT
    grant_status = "מקבל מענק איזון" if has_grant else "לא מקבל מענק"

    total_children = sum(
        _estimate_children(l.budget_topic, l.amount)
        for l in code3_lines
    )

    positions = [
        _analyze_assistants(code19_lines, code3_lines, total_children, divisor, municipality.name, month),
        _analyze_kindergartens(code3_lines, total_children, municipality.name, month),
        _analyze_completion_children(code3_lines, municipality.name, month),
        _analyze_six_day(code19_lines, municipality.name, month),
        _analyze_attendance_officer(officer_lines, total_children, municipality.name, month),
    ]

    missing_items = [p for p in positions if p.gap_direction == "missing" and p.gap > 0]
    surplus_items = [p for p in positions if p.gap_direction == "surplus"]
    ok_items = [p for p in positions if p.gap_direction == "ok"]
    urgent_items = [p for p in positions if p.severity == "critical"]
    total_potential = sum(p.annual_gap_value for p in missing_items)

    return PositionsAnalysisResponse(
        municipality_id=municipality.id,
        municipality_name=municipality.name,
        month=month,
        grant_status=grant_status,
        divisor=divisor,
        total_children=total_children,
        summary=Summary(
            total_positions_analyzed=len(positions),
            positions_ok=len(ok_items),
            positions_missing=len(missing_items),
            positions_surplus=len(surplus_items),
            total_potential_value=round(total_potential),
            urgent_count=len(urgent_items),
        ),
        positions=positions,
        has_data=True,
    )


# ──────────────────────────────────────────────────────────
# Admin summary schemas
# ──────────────────────────────────────────────────────────
class MunicipalityPositionSummary(BaseModel):
    id: int
    name: str
    code: str
    grant_status: str
    divisor: int
    total_children: int
    total_potential_value: float
    alert_level: str          # "critical" | "attention" | "ok" | "no_data"
    has_data: bool
    positions: Dict[str, Any]  # keyed by position id


class GrandSummary(BaseModel):
    total_potential_value: float
    total_urgent: int
    total_attention: int
    total_ok: int


class AdminSummaryResponse(BaseModel):
    month: str
    generated_at: str
    total_municipalities: int
    municipalities_with_data: int
    municipalities_no_data: int
    grand_summary: GrandSummary
    municipalities: List[MunicipalityPositionSummary]


# ──────────────────────────────────────────────────────────
# Municipality endpoint
# ──────────────────────────────────────────────────────────
@router.get("/analysis/{municipality_id}/{month}", response_model=PositionsAnalysisResponse)
async def get_positions_analysis(
    municipality_id: int,
    month: str,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """
    Returns a full positions & quotas analysis for the given municipality + month.
    Municipality users can only access their own data.
    Auto-saves gap history for trending.
    """
    if current_user.role == "municipality":
        if current_user.municipality_id != municipality_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="אין הרשאה לצפות בנתוני רשות אחרת",
            )

    municipality = db.query(Municipality).filter(Municipality.id == municipality_id).first()
    if not municipality:
        raise HTTPException(status_code=404, detail="הרשות המקומית לא נמצאה")

    result = calculate_positions_for_municipality(municipality, month, db)

    # Auto-save gap history for trending
    if result.has_data:
        try:
            from backend.routes.deadlines import save_gap_history
            save_gap_history(db, municipality_id, month, result.positions)
        except Exception as e:
            logger.warning(f"Gap history save skipped: {e}")

    return result


# ──────────────────────────────────────────────────────────
# Admin summary endpoint — all municipalities
# ──────────────────────────────────────────────────────────
@router.get("/admin-summary/{month}", response_model=AdminSummaryResponse)
async def get_admin_positions_summary(
    month: str,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """
    Admin-only endpoint. Returns position analysis summary for ALL municipalities.
    """
    if current_user.role not in ("admin",):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="הגישה מוגבלת למנהלי מערכת בלבד",
        )

    from datetime import datetime as dt
    all_municipalities = db.query(Municipality).all()

    results: List[MunicipalityPositionSummary] = []
    with_data = 0
    no_data = 0
    grand_potential = 0.0
    grand_urgent = 0
    grand_attention = 0
    grand_ok = 0

    for muni in all_municipalities:
        analysis = calculate_positions_for_municipality(muni, month, db)

        if not analysis.has_data:
            no_data += 1
            results.append(MunicipalityPositionSummary(
                id=muni.id,
                name=muni.name,
                code=muni.code,
                grant_status="לא ידוע",
                divisor=DIVISOR_WITHOUT_GRANT,
                total_children=0,
                total_potential_value=0,
                alert_level="no_data",
                has_data=False,
                positions={},
            ))
            continue

        with_data += 1
        grand_potential += analysis.summary.total_potential_value
        grand_urgent += analysis.summary.urgent_count

        # Convert positions list to dict keyed by id
        positions_dict = {}
        for p in analysis.positions:
            positions_dict[p.id] = {
                "current": p.current,
                "entitled": p.entitled,
                "gap": p.gap,
                "gap_direction": p.gap_direction,
                "status": p.status,
                "severity": p.severity,
                "annual_value": p.annual_gap_value,
                "monthly_value": p.monthly_gap_value,
            }

        # Determine alert level for this municipality
        if analysis.summary.urgent_count > 0:
            alert_level = "critical"
        elif analysis.summary.positions_missing > 0:
            alert_level = "attention"
            grand_attention += analysis.summary.positions_missing
        else:
            alert_level = "ok"
            grand_ok += 1

        results.append(MunicipalityPositionSummary(
            id=muni.id,
            name=muni.name,
            code=muni.code,
            grant_status=analysis.grant_status,
            divisor=analysis.divisor,
            total_children=analysis.total_children,
            total_potential_value=analysis.summary.total_potential_value,
            alert_level=alert_level,
            has_data=True,
            positions=positions_dict,
        ))

    # Sort: with data first, then by potential value desc
    results.sort(key=lambda r: (-r.total_potential_value, r.name))

    return AdminSummaryResponse(
        month=month,
        generated_at=dt.now().isoformat(),
        total_municipalities=len(all_municipalities),
        municipalities_with_data=with_data,
        municipalities_no_data=no_data,
        grand_summary=GrandSummary(
            total_potential_value=round(grand_potential),
            total_urgent=grand_urgent,
            total_attention=grand_attention,
            total_ok=grand_ok,
        ),
        municipalities=results,
    )
