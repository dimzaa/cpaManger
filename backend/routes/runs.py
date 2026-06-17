"""
Monthly runs routes.

Endpoints for:
- List all monthly runs (with optional filtering)
- Get a specific monthly run
- Get runs for a specific municipality
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from typing import Literal, Optional
from datetime import datetime
from pydantic import BaseModel

from backend.database import get_db
from backend.models import MonthlyRun, Municipality, BudgetLine, User
from backend.models.ingestion_warning import IngestionWarning
from backend.schemas import MonthlyRunSummary, MonthlyRun as MonthlyRunSchema
from backend.utils.auth_guards import require_login, require_admin
from backend.routes.auth import log_action

router = APIRouter(
    prefix="/api/runs",
    tags=["runs"],
)

admin_router = APIRouter(
    prefix="/api/admin/runs",
    tags=["runs"],
)


class ReviewStatusUpdate(BaseModel):
    status: Literal["pending", "in_review", "reviewed", "flagged"]
    note: Optional[str] = None


def _reviewer_name(user: Optional[User]) -> Optional[str]:
    if not user:
        return None
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return full_name or user.email


@router.get("/available-months", response_model=List[str])
def get_available_months(
    include_test: bool = False,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    """Return distinct months that have at least one uploaded run, newest first."""
    query = db.query(MonthlyRun.month).join(
        Municipality,
        Municipality.id == MonthlyRun.municipality_id,
    )

    if not include_test or current_user.role != "admin":
        query = query.filter(Municipality.is_test == False)

    months = (
        query.distinct()
        .order_by(MonthlyRun.month.desc())
        .all()
    )

    return [row[0] for row in months if row and row[0]]


@router.get("/", response_model=List[MonthlyRunSummary])
def list_all_runs(
    municipality_id: int = None,
    month: str = None,
    status_filter: str = None,
    review_status: str = None,
    include_test: bool = False,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    """
    List all monthly runs with optional filtering.
    
    **Requires authentication.** Municipality users only see their own runs.
    
    Args:
        municipality_id: Filter by municipality (optional)
        month: Filter by month in YYYY-MM format (optional)
        status_filter: Filter by status (pending/processed/error) (optional)
        db: Database session
        
    Returns:
        List of monthly runs
    """
    query = db.query(MonthlyRun).join(
        Municipality,
        Municipality.id == MonthlyRun.municipality_id,
    )

    # Filter out test municipalities unless explicitly requested by an admin
    if not include_test or current_user.role != "admin":
        query = query.filter(Municipality.is_test == False)
    
    # If municipality user, filter by their municipality
    if current_user.role == "municipality" and not municipality_id:
        municipality_id = current_user.municipality_id
    
    if municipality_id:
        # Check access if filtering by specific municipality
        if current_user.role == "municipality" and current_user.municipality_id != municipality_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this municipality's runs"
            )
        query = query.filter(MonthlyRun.municipality_id == municipality_id)
    
    if month:
        query = query.filter(MonthlyRun.month == month)
    
    if status_filter:
        query = query.filter(MonthlyRun.status == status_filter)

    if review_status:
        query = query.filter(MonthlyRun.review_status == review_status)
    
    runs = query.order_by(MonthlyRun.uploaded_at.desc()).all()

    # Enrich each run with retro payment info from budget lines
    result = []
    for run in runs:
        retro_lines = db.query(BudgetLine).filter(
            BudgetLine.run_id == run.id,
            BudgetLine.is_retro == True
        ).all()
        has_retro = len(retro_lines) > 0
        retro_total = sum(float(line.amount) for line in retro_lines if line.amount is not None)

        run_dict = {
            "id": run.id,
            "municipality_id": run.municipality_id,
            "month": run.month,
            "year": run.year,
            "status": run.status,
            "is_balanced": run.is_balanced,
            "invoice_total": run.invoice_total,
            "breakdown_total": run.breakdown_total,
            "difference": run.difference,
            "has_retro": has_retro,
            "retro_total": retro_total if has_retro else None,
            "review_status": run.review_status or "pending",
            "reviewed_by_user_id": run.reviewed_by_user_id,
            "reviewed_at": run.reviewed_at,
            "reviewer_name": _reviewer_name(run.reviewer),
            "uploaded_at": run.uploaded_at,
        }
        result.append(run_dict)

    return result


@router.get("/{run_id}", response_model=MonthlyRunSchema)
def get_run(run_id: int, db: Session = Depends(get_db)):
    """
    Get a specific monthly run by ID.
    
    Args:
        run_id: ID of the monthly run
        
    Returns:
        Monthly run details
        
    Raises:
        HTTPException 404: If run not found
    """
    run = db.query(MonthlyRun).filter(MonthlyRun.id == run_id).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )
    
    return run


@router.get("/municipality/{municipality_id}", response_model=List[MonthlyRunSummary])
def get_municipality_runs(
    municipality_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all monthly runs for a specific municipality.
    
    Args:
        municipality_id: ID of the municipality
        
    Returns:
        List of monthly runs for that municipality, sorted by month (newest first)
        
    Raises:
        HTTPException 404: If municipality not found
    """
    # Verify municipality exists
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Municipality {municipality_id} not found"
        )
    
    runs = db.query(MonthlyRun).filter(
        MonthlyRun.municipality_id == municipality_id
    ).order_by(MonthlyRun.month.desc()).all()
    
    return runs


@router.get("/municipality/{municipality_id}/{month}", response_model=MonthlyRunSchema)
def get_municipality_month_run(
    municipality_id: int,
    month: str,
    db: Session = Depends(get_db)
):
    """
    Get the monthly run for a specific municipality and month.
    
    Args:
        municipality_id: ID of the municipality
        month: Month in YYYY-MM format
        
    Returns:
        Monthly run details
        
    Raises:
        HTTPException 404: If run not found
    """
    run = db.query(MonthlyRun).filter(
        MonthlyRun.municipality_id == municipality_id,
        MonthlyRun.month == month,
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run for municipality {municipality_id} in month {month} not found"
        )
    
    return run


@admin_router.patch("/{run_id}/review-status", response_model=MonthlyRunSchema)
def update_run_review_status(
    run_id: int,
    payload: ReviewStatusUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    run = db.query(MonthlyRun).filter(MonthlyRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    if payload.status == "flagged" and not (payload.note or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flagged status requires a note",
        )

    run.review_status = payload.status
    run.review_status_note = (payload.note or "").strip() or None

    if payload.status in {"reviewed", "flagged"}:
        run.reviewed_by_user_id = current_user.id
        run.reviewed_at = datetime.utcnow()
    else:
        run.reviewed_by_user_id = None
        run.reviewed_at = None

    db.commit()
    db.refresh(run)

    log_action(
        db=db,
        user_id=current_user.id,
        action="update_review_status",
        endpoint=f"PATCH /api/admin/runs/{run_id}/review-status",
        method="PATCH",
        resource_type="monthly_run",
        resource_id=run.id,
        status_code=200,
    )

    # Attach reviewer_name dynamically for response model
    run.reviewer_name = _reviewer_name(run.reviewer)
    return run


class IngestionWarningOut(BaseModel):
    id: int
    severity: str
    category: str
    file_type: Optional[str] = None
    topic_code: Optional[str] = None
    detail_sum: Optional[float] = None
    aux_sum: Optional[float] = None
    cheshbonit_sum: Optional[float] = None
    delta: Optional[float] = None
    message: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("/{run_id}/warnings", response_model=List[IngestionWarningOut])
def get_run_warnings(
    run_id: int,
    severity: Optional[Literal["info", "warn", "error"]] = None,
    category: Optional[str] = None,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Return the structured ingestion warnings persisted for this run.

    These mirror the parser's ``⚠️``/``✓`` stdout lines and let the admin
    UI surface tie-out anomalies without grepping the upload log.
    """
    run = db.query(MonthlyRun).filter(MonthlyRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    q = db.query(IngestionWarning).filter(IngestionWarning.run_id == run_id)
    if severity:
        q = q.filter(IngestionWarning.severity == severity)
    if category:
        q = q.filter(IngestionWarning.category == category)
    # Order: errors first, then warns, then info; within severity by id.
    sev_order = {"error": 0, "warn": 1, "info": 2}
    rows = sorted(q.all(), key=lambda r: (sev_order.get(r.severity, 9), r.id))
    return rows
