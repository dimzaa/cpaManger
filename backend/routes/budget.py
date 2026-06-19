"""
Budget routes for retrieving budget data for municipalities.

Main endpoint for:
- Getting full budget breakdown for a municipality in a specific month
- Comparing months
- Viewing budget details with explanations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
from dateutil.relativedelta import relativedelta

from backend.database import get_db
from backend.models import Municipality, MonthlyRun, BudgetLine, BudgetLineInstitution, User, TopicSummary
from backend.models.approved_explanation import ApprovedExplanation
from backend.schemas import BudgetLineResponse
from backend.services.student_count_delta import compute_student_count_delta
from backend.services.variance_driver_classifier import (
    build_explanation_prefix,
    classify,
)
from backend.utils.auth_guards import require_login, require_municipality_access
from backend.utils.high_school_codes import HIGH_SCHOOL_CODES
from backend.utils.serializers import bytes_to_string

router = APIRouter(
    prefix="/api/budget",
    tags=["budget"],
)


def _build_topic_breakdown_payload(db: Session, run_id: int, municipality_id: int, topic_code: str) -> Optional[Dict[str, Any]]:
    parent_lines = (
        db.query(BudgetLine)
        .filter(
            BudgetLine.run_id == run_id,
            BudgetLine.municipality_id == municipality_id,
            BudgetLine.topic_code == topic_code,
        )
        .all()
    )
    if not parent_lines:
        return None

    total = sum(float(line.amount or 0.0) for line in parent_lines)
    topic_name = bytes_to_string(parent_lines[0].budget_topic)
    line_ids = [line.id for line in parent_lines]

    rows = (
        db.query(BudgetLineInstitution)
        .filter(BudgetLineInstitution.budget_line_id.in_(line_ids))
        .all()
    )

    grouped = {}
    for row in rows:
        key = (
            bytes_to_string(row.institution_code),
            bytes_to_string(row.institution_name) if row.institution_name else None,
            bytes_to_string(row.source_file) if row.source_file else None,
        )
        if key not in grouped:
            grouped[key] = {
                "institution_code": key[0],
                "institution_name": key[1],
                "amount": 0.0,
                "num_children": row.num_children,
                "participation_pct": row.participation_pct,
                "source_file": key[2],
            }
        grouped[key]["amount"] += float(row.amount or 0.0)

    institutions = sorted(grouped.values(), key=lambda item: float(item["amount"]), reverse=True)

    return {
        "run_id": run_id,
        "municipality_id": municipality_id,
        "topic_code": topic_code,
        "topic_name": topic_name,
        "total": round(total, 2),
        "institutions": [
            {
                **item,
                "amount": round(float(item["amount"]), 2),
            }
            for item in institutions
        ],
    }


@router.get("/runs/{run_id}/municipalities/{municipality_id}/topic-lines/{topic_code}")
def get_topic_budget_lines(
    run_id: int,
    municipality_id: int,
    topic_code: str,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Phase 3.1 drill-down: return every BudgetLine row for a single topic.

    After Phase 1, each detail/aux file emits per-row ``BudgetLine`` rows
    (line_type = gy / mutavim / sharatim / shefi / hasaot / mucarim /
    yadaniim / moadon / sacal), each carrying its own amount,
    period_month, num_children, participation_pct, and notes.

    The main ``/budget/{muni}/{month}`` endpoint AGGREGATES these into a
    single row per topic_code. This endpoint returns the un-aggregated
    rows so the UI can expand a topic and show its constituent lines.
    """
    require_municipality_access(municipality_id, current_user)

    run = (
        db.query(MonthlyRun)
        .filter(
            MonthlyRun.id == run_id,
            MonthlyRun.municipality_id == municipality_id,
        )
        .first()
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    lines = (
        db.query(BudgetLine)
        .filter(
            BudgetLine.run_id == run_id,
            BudgetLine.municipality_id == municipality_id,
            BudgetLine.topic_code == str(topic_code),
        )
        .order_by(BudgetLine.line_type, BudgetLine.amount.desc())
        .all()
    )

    if not lines:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No budget lines for topic {topic_code}",
        )

    # Aggregate by line_type so the UI can show "SACAL: 930 rows / ₪X"
    # section headers.
    by_type: Dict[str, Dict[str, Any]] = {}
    for line in lines:
        lt = bytes_to_string(line.line_type) or "regular"
        bucket = by_type.setdefault(lt, {"count": 0, "total": 0.0})
        bucket["count"] += 1
        bucket["total"] += float(line.amount or 0.0)

    rows = [
        {
            "id": line.id,
            "line_type": bytes_to_string(line.line_type),
            "amount": round(float(line.amount or 0.0), 2),
            "period_month": line.period_month,
            "current_month": line.current_month,
            "is_retro": bool(line.is_retro),
            "num_children": line.num_children,
            "participation_pct": line.participation_pct,
            "notes": bytes_to_string(line.notes),
            "variance_driver": bytes_to_string(line.variance_driver),
        }
        for line in lines
    ]

    return {
        "run_id": run_id,
        "municipality_id": municipality_id,
        "topic_code": str(topic_code),
        "topic_name": bytes_to_string(lines[0].budget_topic),
        "total": round(sum(r["amount"] for r in rows), 2),
        "row_count": len(rows),
        "by_line_type": {
            lt: {"count": v["count"], "total": round(v["total"], 2)}
            for lt, v in sorted(by_type.items())
        },
        "rows": rows,
    }


@router.get("/runs/{run_id}/municipalities/{municipality_id}/institutions")
def get_topic_institution_breakdown(
    run_id: int,
    municipality_id: int,
    topic_code: str,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    require_municipality_access(municipality_id, current_user)

    run = db.query(MonthlyRun).filter(MonthlyRun.id == run_id, MonthlyRun.municipality_id == municipality_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    payload = _build_topic_breakdown_payload(db, run_id, municipality_id, str(topic_code))
    if not payload or not payload["institutions"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No institution breakdown for this topic")

    return payload


@router.get("/runs/{run_id}/student-count-deltas")
def get_student_count_deltas(
    run_id: int,
    municipality_id: int,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Per-budget-line student-count delta vs. the most recent prior run.

    Returns only rows where both the current and prior ``num_children`` are
    known (zero is a real value; only None means unknown) and at least one of
    amount or count actually moved. Sorted by ``abs(delta_amount)`` DESC.
    """
    require_municipality_access(municipality_id, current_user)

    run = (
        db.query(MonthlyRun)
        .filter(MonthlyRun.id == run_id, MonthlyRun.municipality_id == municipality_id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    lines = (
        db.query(BudgetLine)
        .filter(
            BudgetLine.run_id == run_id,
            BudgetLine.municipality_id == municipality_id,
        )
        .all()
    )

    deltas: List[Dict[str, Any]] = []
    prev_run_ids = set()
    for line in lines:
        delta = compute_student_count_delta(
            db=db,
            current_run_id=run_id,
            municipality_id=municipality_id,
            topic_code=str(line.topic_code),
            period_month=str(line.period_month),
        )
        if delta is None:
            continue
        if delta.delta_amount == 0 and delta.delta_children == 0:
            continue
        driver = classify(delta)
        prev_run_ids.add(delta.prev_run_id)
        deltas.append({
            "topic_code": str(line.topic_code),
            "topic_name": bytes_to_string(line.budget_topic),
            "period_month": str(line.period_month),
            "prev_num_children": delta.prev_num_children,
            "curr_num_children": delta.curr_num_children,
            "delta_children": delta.delta_children,
            "prev_amount": round(delta.prev_amount, 2),
            "curr_amount": round(delta.curr_amount, 2),
            "delta_amount": round(delta.delta_amount, 2),
            "expected_amount_from_count": round(delta.expected_amount_from_count, 2),
            "explained_amount": round(delta.explained_amount, 2),
            "explained_ratio": (
                round(delta.explained_ratio, 4) if delta.explained_ratio is not None else None
            ),
            "residual_amount": round(delta.residual_amount, 2),
            "variance_driver": driver,
        })

    deltas.sort(key=lambda row: abs(row["delta_amount"]), reverse=True)

    previous_run_id = next(iter(prev_run_ids)) if len(prev_run_ids) == 1 else None

    return {
        "run_id": run_id,
        "municipality_id": municipality_id,
        "previous_run_id": previous_run_id,
        "lines": deltas,
    }


@router.get("/runs/{run_id}/municipalities/{municipality_id}/high-school-breakdown")
def get_high_school_breakdown(
    run_id: int,
    municipality_id: int,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    require_municipality_access(municipality_id, current_user)

    run = db.query(MonthlyRun).filter(MonthlyRun.id == run_id, MonthlyRun.municipality_id == municipality_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    result = {}
    for code in sorted(HIGH_SCHOOL_CODES):
        payload = _build_topic_breakdown_payload(db, run_id, municipality_id, code)
        if payload and payload["institutions"]:
            result[code] = payload

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No high-school institution breakdown for this run")

    return {
        "run_id": run_id,
        "municipality_id": municipality_id,
        "topics": result,
    }


@router.get("/{municipality_id}/{month}")
def get_budget_for_month(
    municipality_id: int,
    month: str,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get complete budget data for a municipality in a specific month.
    
    **Requires authentication.** Municipality users can only access their own municipality.
    
    This is the main endpoint for municipality employees to view their budget.
    Returns all budget lines with explanations and cross-reference data.
    
    Args:
        municipality_id: ID of the municipality
        month: Month in YYYY-MM format (e.g., "2024-03")
        current_user: Authenticated user
        
    Returns:
        {
            "municipality": {
                "id": int,
                "name": str,
                "code": str,
            },
            "month": str,
            "status": "processed" | "pending" | "error" | "not_found",
            "invoice_total": float,
            "breakdown_total": float,
            "is_balanced": bool,
            "difference": float,
            "budget_lines": [
                {
                    "id": int,
                    "budget_topic": str,
                    "topic_code": str,
                    "amount": float,
                    "period_month": str,
                    "line_type": str,
                    "is_retro": bool,
                    "notes": str,
                }
            ],
            "summary_by_topic": {
                "topic_code": {
                    "topic_name": str,
                    "total": float,
                    "lines_count": int,
                    "has_retro": bool,
                }
            },
            "uploaded_at": datetime,
        }
        
    Raises:
        HTTPException 403: If user cannot access this municipality
        HTTPException 404: If municipality or run not found
    """
    
    try:
        print(f"\n📊 BUDGET DATA DEBUG:")
        print(f"   Municipality ID: {municipality_id}")
        print(f"   Month: {month}")
        print(f"   User: {current_user.email} (Role: {current_user.role})")
        
        # Check municipality access (admins can access all, municipality users only their own)
        require_municipality_access(municipality_id, current_user)
        
        # Verify municipality exists
        municipality = db.query(Municipality).filter(
            Municipality.id == municipality_id
        ).first()
        
        if not municipality:
            print(f"   ❌ Municipality {municipality_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Municipality {municipality_id} not found"
            )
    
        # Get the monthly run
        all_runs = db.query(MonthlyRun).filter(
            MonthlyRun.municipality_id == municipality_id
        ).all()
        print(f"   Runs for this municipality: {len(all_runs)}")
        for r in all_runs:
            print(f"      - {r.month} (ID: {r.id}, Status: {r.status})")
        
        run = db.query(MonthlyRun).filter(
            MonthlyRun.municipality_id == municipality_id,
            MonthlyRun.month == month,
        ).first()
        
        if not run:
            print(f"   ❌ No run found for {month}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No budget data found for municipality {municipality_id} in month {month}"
            )
        
        print(f"   ✅ Found run ID: {run.id}")
        
        # Get budget lines for this run
        raw_budget_lines = db.query(BudgetLine).filter(
            BudgetLine.run_id == run.id
        ).order_by(BudgetLine.topic_code).all()

        # Drop placeholder/garbage rows: blank topic_code (or '0') with zero
        # amount AND no topic name. Same rule as analytics._is_real_line().
        def _is_real_line(l):
            code = (bytes_to_string(l.topic_code) or '').strip()
            if not code or code == '0':
                amt = float(l.amount or 0)
                topic = (bytes_to_string(l.budget_topic) or '').strip()
                if amt == 0 and not topic:
                    return False
            return True

        budget_lines = [l for l in raw_budget_lines if _is_real_line(l)]
        print(f"   Budget lines found: {len(budget_lines)} (filtered from {len(raw_budget_lines)})")

        # Compute the authoritative sum-of-lines. If the run's stored
        # breakdown_total disagrees with the line sum (seed bug / parser
        # inconsistency), expose the computed total so the UI can show
        # something trustworthy + flag the mismatch.
        lines_sum = round(sum(float(l.amount or 0) for l in budget_lines), 2)
        lines_sum_regular = round(
            sum(float(l.amount or 0) for l in budget_lines if not l.is_retro), 2
        )
        lines_sum_retro = round(
            sum(float(l.amount or 0) for l in budget_lines if l.is_retro), 2
        )
        retro_pos = round(
            sum(float(l.amount or 0) for l in budget_lines
                if l.is_retro and float(l.amount or 0) > 0), 2
        )
        retro_neg = round(
            sum(float(l.amount or 0) for l in budget_lines
                if l.is_retro and float(l.amount or 0) < 0), 2
        )
        stored_breakdown = float(run.breakdown_total) if run.breakdown_total is not None else 0.0
        breakdown_mismatch = abs(lines_sum - stored_breakdown) > 1.0
        
        # Get approved explanations for this month/municipality
        approved_explanations = db.query(ApprovedExplanation).filter(
            ApprovedExplanation.municipality_id == municipality_id,
            ApprovedExplanation.month == month
        ).all()
        
        approved_exp_map = {}
        for ae in approved_explanations:
            key = (ae.budget_line_id, ae.topic_code)
            approved_exp_map[key] = ae.final_text
        
        print(f"   Approved explanations found: {len(approved_explanations)}")
        
        # Build response
        response = {
            "municipality": {
                "id": municipality.id,
                "name": bytes_to_string(municipality.name),  # Convert bytes to string
                "code": bytes_to_string(municipality.code),  # Convert bytes to string
            },
            "run_id": run.id,
            "month": bytes_to_string(month),  # Convert bytes to string
            "status": bytes_to_string(run.status),  # Convert bytes to string
            "invoice_total": float(run.invoice_total) if run.invoice_total is not None else 0.0,  # Ensure float
            "breakdown_total": stored_breakdown,  # As stored on the run row
            "lines_sum": lines_sum,  # Sum of *actual* filtered lines (authoritative)
            "lines_sum_regular": lines_sum_regular,
            "lines_sum_retro": lines_sum_retro,
            "retro_positive": retro_pos,
            "retro_negative": retro_neg,
            "breakdown_mismatch": breakdown_mismatch,
            "is_balanced": run.is_balanced,
            "difference": float(run.difference) if run.difference is not None else 0.0,  # Ensure float
            "review_status": run.review_status or "pending",
            "reviewed_at": run.reviewed_at.isoformat() if run.reviewed_at else None,
            "reviewed_by_user_id": run.reviewed_by_user_id,
            "reviewed_by_name": (
                f"{(run.reviewer.first_name or '').strip()} {(run.reviewer.last_name or '').strip()}".strip()
                if run.reviewer else None
            ) or (run.reviewer.email if run.reviewer else None),
            "uploaded_at": run.uploaded_at.isoformat(),
            "file_name": bytes_to_string(run.file_name),  # Convert bytes to string
            "budget_lines": [
                {
                    "id": line.id,
                    "budget_topic": bytes_to_string(line.budget_topic),  # Convert bytes
                    "topic_code": bytes_to_string(line.topic_code),  # Convert bytes
                    "amount": float(line.amount) if line.amount is not None else 0.0,
                    "period_month": bytes_to_string(line.period_month),  # Convert bytes
                    "current_month": bytes_to_string(line.current_month),  # Convert bytes
                    "line_type": bytes_to_string(line.line_type),  # Convert bytes
                    "is_retro": line.is_retro,
                    "notes": bytes_to_string(line.notes) if line.notes else None,  # Convert bytes
                    "approved_explanation": approved_exp_map.get((line.id, bytes_to_string(line.topic_code)), None),  # Include approved explanation if exists
                }
                for line in budget_lines
            ],
        }

        # Keep reviewer notes admin-only.
        if current_user.role == "admin":
            response["review_status_note"] = run.review_status_note
        
        # Build summary by topic
        summary_by_topic = {}
        for line in budget_lines:
            code = bytes_to_string(line.topic_code)  # Convert bytes to string
            if code not in summary_by_topic:
                summary_by_topic[code] = {
                    "topic_name": bytes_to_string(line.budget_topic),  # Convert bytes
                    "total": 0,
                    "lines_count": 0,
                    "has_retro": False,
                    "has_shortage": False,
                }
            
            summary_by_topic[code]["total"] += float(line.amount) if line.amount is not None else 0.0
            summary_by_topic[code]["lines_count"] += 1
            if line.is_retro:
                summary_by_topic[code]["has_retro"] = True
            if bytes_to_string(line.line_type) == "shortage":  # Convert bytes to string
                summary_by_topic[code]["has_shortage"] = True
        
        response["summary_by_topic"] = summary_by_topic
        
        # Calculate changes from previous month
        changes = calculate_month_changes(db, municipality_id, month)
        if changes:
            response["month_changes"] = changes
        
        print(f"   ✅ Returning budget data with {len(budget_lines)} lines")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"   ❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching budget data: {str(e)}"
        )


@router.get("/{municipality_id}/history/{num_months}")
def get_budget_history(
    municipality_id: int,
    num_months: int = 3,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get budget history for a municipality (last N months).
    
    **Requires authentication.** Municipality users can only access their own municipality.
    
    Useful for comparing months and identifying trends.
    
    Args:
        municipality_id: ID of the municipality
        num_months: Number of months to return (default 3, max 12)
        
    Returns:
        {
            "municipality": {...},
            "months": {
                "2024-03": {...full budget data...},
                "2024-02": {...},
                "2024-01": {...},
            },
            "total_months": int,
        }
        
    Raises:
        HTTPException 403: If user cannot access this municipality
        HTTPException 404: If municipality not found
    """
    
    # Check municipality access
    require_municipality_access(municipality_id, current_user)
    
    # Verify municipality exists
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Municipality {municipality_id} not found"
        )
    
    # Limit num_months to max 12
    num_months = min(num_months, 12)
    
    # Get recent monthly runs
    runs = db.query(MonthlyRun).filter(
        MonthlyRun.municipality_id == municipality_id,
    ).order_by(MonthlyRun.month.desc()).limit(num_months).all()
    
    # Build response with data for each month
    months_data = {}
    
    for run in runs:
        budget_lines = db.query(BudgetLine).filter(
            BudgetLine.run_id == run.id
        ).all()
        
        months_data[run.month] = {
            "month": run.month,
            "status": run.status,
            "invoice_total": run.invoice_total,
            "breakdown_total": run.breakdown_total,
            "is_balanced": run.is_balanced,
            "difference": run.difference,
            "uploaded_at": run.uploaded_at.isoformat(),
            "budget_lines": [
                {
                    "budget_topic": line.budget_topic,
                    "topic_code": line.topic_code,
                    "amount": line.amount,
                    "period_month": line.period_month,
                    "line_type": line.line_type,
                    "is_retro": line.is_retro,
                }
                for line in budget_lines
            ],
        }
    
    return {
        "municipality": {
            "id": municipality.id,
            "name": municipality.name,
            "code": municipality.code,
        },
        "months": months_data,
        "total_months": len(months_data),
    }


@router.get("/{municipality_id}/{month}/anomalies")
def get_budget_anomalies(
    municipality_id: int,
    month: str,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get anomalies detected in a month's budget.
    
    **Requires authentication.** Municipality users can only access their own municipality.
    
    Includes:
    - Retro payments (period_month != current_month)
    - Shortages (less than previous month)
    - Imbalances (invoice_total != breakdown_total)
    
    Args:
        municipality_id: ID of the municipality
        month: Month in YYYY-MM format
        
    Returns:
        {
            "municipality": {...},
            "month": str,
            "has_anomalies": bool,
            "retro_payments": [...],
            "shortages": [...],
            "imbalance": {...},
        }
        
    Raises:
        HTTPException 403: If user cannot access this municipality
    """
    
    # Check municipality access
    require_municipality_access(municipality_id, current_user)
    
    # Verify municipality exists
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Municipality {municipality_id} not found"
        )
    
    # Get the monthly run
    run = db.query(MonthlyRun).filter(
        MonthlyRun.municipality_id == municipality_id,
        MonthlyRun.month == month,
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No budget data found for municipality {municipality_id} in month {month}"
        )
    
    # Get budget lines
    budget_lines = db.query(BudgetLine).filter(
        BudgetLine.run_id == run.id
    ).all()
    
    # Find retro payments
    retro_payments = [
        {
            "budget_topic": line.budget_topic,
            "topic_code": line.topic_code,
            "amount": line.amount,
            "period_month": line.period_month,
            "notes": line.notes,
        }
        for line in budget_lines if line.is_retro
    ]
    
    # Find shortages
    shortages = [
        {
            "budget_topic": line.budget_topic,
            "topic_code": line.topic_code,
            "amount": line.amount,
            "notes": line.notes,
        }
        for line in budget_lines if line.line_type == "shortage"
    ]
    
    # Check imbalance
    imbalance = None
    if not run.is_balanced and run.difference != 0:
        imbalance = {
            "difference": run.difference,
            "percentage": abs(run.difference) / run.invoice_total * 100 if run.invoice_total else 0,
            "explanation": "סכום התקציב שצוין בתעודה לא תואם לסכום פירוט הנושאים" 
                          if run.difference > 0
                          else "יש עודף בפירוט הנושאים בהשוואה לתעודה",
        }
    
    has_anomalies = bool(retro_payments or shortages or imbalance)
    
    return {
        "municipality": {
            "id": municipality.id,
            "name": municipality.name,
            "code": municipality.code,
        },
        "month": month,
        "has_anomalies": has_anomalies,
        "retro_payments": retro_payments,
        "shortages": shortages,
        "imbalance": imbalance,
    }


# ==============================================================================
# HELPER FUNCTION: Calculate changes between consecutive months
# ==============================================================================

def calculate_month_changes(
    db: Session,
    municipality_id: int,
    current_month: str,
) -> Optional[Dict[str, Any]]:
    """Calculate changes between the current month and the most recent
    prior month for which this municipality has a processed run.

    Returns a dict with structure::

        {
            "previous_month": "2026-02",
            "has_changes": bool,
            "changes_by_topic": {
                "3": {
                    "topic_name": "גני ילדים",
                    "prev_lines_count": int,
                    "curr_lines_count": int,
                    "items_change":     int,       # curr - prev
                    "prev_total":       float,
                    "curr_total":       float,
                    "amount_change":    float,     # curr - prev
                    "amount_change_pct": float,    # ((curr - prev) / prev) * 100, 0 when prev == 0
                    "topic_code":       str,
                },
                ...
            },
        }

    Returns ``None`` when there is no prior month to compare against.
    """
    # Find the most recent processed run that came before this month.
    prior_run = (
        db.query(MonthlyRun)
        .filter(
            MonthlyRun.municipality_id == municipality_id,
            MonthlyRun.month < current_month,
            MonthlyRun.status == "processed",
        )
        .order_by(MonthlyRun.month.desc(), MonthlyRun.uploaded_at.desc())
        .first()
    )
    if not prior_run:
        return None

    # Most recent run for the current month (may be None — caller already
    # gated on having a run, but be defensive).
    curr_run = (
        db.query(MonthlyRun)
        .filter(
            MonthlyRun.municipality_id == municipality_id,
            MonthlyRun.month == current_month,
            MonthlyRun.status == "processed",
        )
        .order_by(MonthlyRun.uploaded_at.desc())
        .first()
    )
    if not curr_run:
        return None

    prev_lines = (
        db.query(BudgetLine)
        .filter(
            BudgetLine.municipality_id == municipality_id,
            BudgetLine.run_id == prior_run.id,
        )
        .all()
    )
    curr_lines = (
        db.query(BudgetLine)
        .filter(
            BudgetLine.municipality_id == municipality_id,
            BudgetLine.run_id == curr_run.id,
        )
        .all()
    )

    def _agg(lines):
        by_code: Dict[str, Dict[str, Any]] = {}
        for ln in lines:
            code = str(ln.topic_code or "").strip()
            if not code:
                continue
            bucket = by_code.setdefault(
                code,
                {
                    "topic_name": ln.budget_topic or "",
                    "lines_count": 0,
                    "total": 0.0,
                },
            )
            bucket["lines_count"] += 1
            bucket["total"] += float(ln.amount or 0.0)
            # Prefer the last-seen Hebrew name in case of minor variations.
            if ln.budget_topic:
                bucket["topic_name"] = ln.budget_topic
        return by_code

    prev_agg = _agg(prev_lines)
    curr_agg = _agg(curr_lines)

    all_codes = set(prev_agg.keys()) | set(curr_agg.keys())
    changes_by_topic: Dict[str, Dict[str, Any]] = {}
    has_changes = False

    for code in all_codes:
        prev = prev_agg.get(code, {"topic_name": "", "lines_count": 0, "total": 0.0})
        curr = curr_agg.get(code, {"topic_name": "", "lines_count": 0, "total": 0.0})

        amount_change = float(curr["total"]) - float(prev["total"])
        items_change = int(curr["lines_count"]) - int(prev["lines_count"])
        prev_total = float(prev["total"])
        if prev_total != 0:
            amount_change_pct = round((amount_change / prev_total) * 100, 1)
        else:
            amount_change_pct = 0.0 if amount_change == 0 else 100.0

        if amount_change != 0 or items_change != 0:
            has_changes = True

        changes_by_topic[code] = {
            "topic_code": code,
            "topic_name": curr["topic_name"] or prev["topic_name"],
            "prev_lines_count": int(prev["lines_count"]),
            "curr_lines_count": int(curr["lines_count"]),
            "items_change": items_change,
            "prev_total": round(prev_total, 2),
            "curr_total": round(float(curr["total"]), 2),
            "amount_change": round(amount_change, 2),
            "amount_change_pct": amount_change_pct,
        }

    return {
        "previous_month": prior_run.month,
        "has_changes": has_changes,
        "changes_by_topic": changes_by_topic,
    }

           

@router.get("/runs/{run_id}/topic-summaries")
def get_topic_summaries(
    run_id: int,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Priority-2 endpoint. Returns the denormalised per-topic snapshot for one run,
    sorted by absolute amount_total descending.

    Each row carries: topic_code/name, the four amount components, MoM delta vs
    previous month, anomaly_flag, tie_out_diff, n_institutions and the top one.

    These rows are populated at upload time by
    ``backend.services.topic_summary_service.recompute_topic_summaries_for_run``.
    """
    run = db.query(MonthlyRun).filter(MonthlyRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    require_municipality_access(run.municipality_id, current_user)

    rows = (
        db.query(TopicSummary)
        .filter(TopicSummary.run_id == run_id)
        .all()
    )
    payload = [
        {
            "id": ts.id,
            "run_id": ts.run_id,
            "municipality_id": ts.municipality_id,
            "topic_code": ts.topic_code,
            "topic_name": bytes_to_string(ts.topic_name),
            "amount_total": ts.amount_total,
            "amount_regular": ts.amount_regular,
            "amount_retro_pos": ts.amount_retro_pos,
            "amount_retro_neg": ts.amount_retro_neg,
            "prev_run_id": ts.prev_run_id,
            "prev_month_amount": ts.prev_month_amount,
            "delta_abs": ts.delta_abs,
            "delta_pct": ts.delta_pct,
            "anomaly_flag": ts.anomaly_flag,
            "tie_out_diff": ts.tie_out_diff,
            "n_institutions": ts.n_institutions,
            "top_institution_code": ts.top_institution_code,
            "top_institution_name": bytes_to_string(ts.top_institution_name),
            "top_institution_amount": ts.top_institution_amount,
        }
        for ts in rows
    ]
    payload.sort(key=lambda r: abs(float(r["amount_total"] or 0.0)), reverse=True)
    return payload
