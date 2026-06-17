"""
/api/reasons routes — CPA access to the reasons library
GET /api/reasons — List all active reasons (with optional filters)
GET /api/reasons/{id} — Get specific reason
POST /api/reasons — Create new reason (CPA only)
PATCH /api/reasons/{id} — Update reason (CPA only)
DELETE /api/reasons/{id} — Soft delete reason (CPA only)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.reason_library import ReasonLibrary
from backend.models.user import User
from backend.utils.auth_guards import require_admin, get_current_user
from backend.services.audit_logger import log_reason_creation, log_reason_update, log_reason_deletion
from typing import Optional, List

router = APIRouter(prefix="/api/reasons", tags=["reasons"])


@router.get("")
async def list_reasons(
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None),
    topic_code: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    active_only: bool = Query(True),
    search: Optional[str] = Query(None),
):
    """
    List reasons with smart filtering
    
    Query params:
    - category: "ילדים", "משרות", "שכר", "גן", "רטרו", "תיקון", "מדיניות", "משפטי", "אחר"
    - topic_code: "3", "19", "33", or "all"
    - direction: "increase", "decrease", "neutral"
    - severity: "routine", "attention", "urgent"
    - active_only: bool (default True)
    - search: substring search in title_hebrew
    """
    query = select(ReasonLibrary)
    
    if active_only:
        query = query.where(ReasonLibrary.is_active == True)
    
    if category:
        query = query.where(ReasonLibrary.category == category)
    
    if direction:
        query = query.where(ReasonLibrary.direction == direction)
    
    if severity:
        query = query.where(ReasonLibrary.severity == severity)
    
    if topic_code:
        # Filter reasons that apply to this topic_code
        # A reason applies if it has "all" or the specific topic_code in its list
        from sqlalchemy import or_
        query = query.where(
            or_(
                ReasonLibrary.topic_codes.contains([topic_code]),
                ReasonLibrary.topic_codes.contains(["all"]),
            )
        )
    
    if search:
        query = query.where(ReasonLibrary.title_hebrew.ilike(f"%{search}%"))
    
    # Sort by sort_order, then by ID
    query = query.order_by(ReasonLibrary.sort_order, ReasonLibrary.id)
    
    reasons = db.execute(query).scalars().all()
    return {
        "data": [r.to_dict() for r in reasons],
        "count": len(reasons),
    }


@router.get("/{reason_id}")
async def get_reason(reason_id: int, db: Session = Depends(get_db)):
    """Get a specific reason by ID"""
    reason = db.execute(
        select(ReasonLibrary).where(ReasonLibrary.id == reason_id)
    ).scalar_one_or_none()
    
    if not reason:
        raise HTTPException(status_code=404, detail="Reason not found")
    
    return {"data": reason.to_dict()}


@router.post("")
async def create_reason(
    reason_data: dict,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new reason (admin/CPA only)
    
    Required fields:
    - code: str (unique)
    - topic_codes: list of strings
    - category: str
    - title_hebrew: str
    - explanation_template: str
    - direction: "increase" | "decrease" | "neutral"
    - severity: "routine" | "attention" | "urgent"
    - requires_detail: bool
    - detail_prompt: str (optional, required if requires_detail=true)
    - sort_order: int (optional)
    """
    # Check if code already exists
    existing = db.execute(
        select(ReasonLibrary).where(ReasonLibrary.code == reason_data.get("code"))
    ).scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Code already exists")
    
    new_reason = ReasonLibrary(
        code=reason_data.get("code"),
        topic_codes=reason_data.get("topic_codes", []),
        category=reason_data.get("category"),
        title_hebrew=reason_data.get("title_hebrew"),
        explanation_template=reason_data.get("explanation_template"),
        direction=reason_data.get("direction", "neutral"),
        severity=reason_data.get("severity", "routine"),
        requires_detail=reason_data.get("requires_detail", False),
        detail_prompt=reason_data.get("detail_prompt"),
        sort_order=reason_data.get("sort_order", 999),
    )
    
    db.add(new_reason)
    db.commit()
    db.refresh(new_reason)
    
    # Log the creation
    log_reason_creation(
        db=db,
        user_id=current_user.id,
        reason_code=new_reason.code,
        reason_id=new_reason.id,
        reason_data=reason_data,
    )
    
    return {"data": new_reason.to_dict(), "message": "Reason created"}


@router.patch("/{reason_id}")
async def update_reason(
    reason_id: int,
    reason_data: dict,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
    current_user: User = Depends(get_current_user),
):
    """Update a reason (admin/CPA only)"""
    reason = db.execute(
        select(ReasonLibrary).where(ReasonLibrary.id == reason_id)
    ).scalar_one_or_none()
    
    if not reason:
        raise HTTPException(status_code=404, detail="Reason not found")
    
    # Capture old values before update
    old_values = {
        "code": reason.code,
        "title_hebrew": reason.title_hebrew,
        "category": reason.category,
        "explanation_template": reason.explanation_template,
        "direction": reason.direction,
        "severity": reason.severity,
        "requires_detail": reason.requires_detail,
        "detail_prompt": reason.detail_prompt,
        "is_active": reason.is_active,
    }
    
    # Update fields
    if "code" in reason_data and reason_data["code"] != reason.code:
        # Check if new code exists
        existing = db.execute(
            select(ReasonLibrary).where(ReasonLibrary.code == reason_data["code"])
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Code already exists")
        reason.code = reason_data["code"]
    
    if "topic_codes" in reason_data:
        reason.topic_codes = reason_data["topic_codes"]
    if "category" in reason_data:
        reason.category = reason_data["category"]
    if "title_hebrew" in reason_data:
        reason.title_hebrew = reason_data["title_hebrew"]
    if "explanation_template" in reason_data:
        reason.explanation_template = reason_data["explanation_template"]
    if "direction" in reason_data:
        reason.direction = reason_data["direction"]
    if "severity" in reason_data:
        reason.severity = reason_data["severity"]
    if "requires_detail" in reason_data:
        reason.requires_detail = reason_data["requires_detail"]
    if "detail_prompt" in reason_data:
        reason.detail_prompt = reason_data["detail_prompt"]
    if "is_active" in reason_data:
        reason.is_active = reason_data["is_active"]
    if "sort_order" in reason_data:
        reason.sort_order = reason_data["sort_order"]
    
    db.commit()
    db.refresh(reason)
    
    # Log the update
    log_reason_update(
        db=db,
        user_id=current_user.id,
        reason_code=reason.code,
        reason_id=reason.id,
        old_data=old_values,
        new_data=reason_data,
    )
    
    return {"data": reason.to_dict(), "message": "Reason updated"}


@router.delete("/{reason_id}")
async def delete_reason(
    reason_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
    current_user: User = Depends(get_current_user),
):
    """Soft delete a reason (admin/CPA only) — marks is_active=false"""
    reason = db.execute(
        select(ReasonLibrary).where(ReasonLibrary.id == reason_id)
    ).scalar_one_or_none()
    
    if not reason:
        raise HTTPException(status_code=404, detail="Reason not found")
    
    # Capture data before deletion
    reason_data_before = reason.to_dict()
    
    reason.is_active = False
    db.commit()
    
    # Log the deletion
    log_reason_deletion(
        db=db,
        user_id=current_user.id,
        reason_code=reason.code,
        reason_id=reason.id,
        reason_data=reason_data_before,
    )
    
    return {"message": "Reason deactivated"}
