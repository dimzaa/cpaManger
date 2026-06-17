"""
Explanation Suggestions Routes

Endpoints for employees to suggest explanations and for admins to approve/reject them.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from backend.database import get_db
from backend.models.user import User, UserRole
from backend.models.explanation_suggestion import ExplanationSuggestion, SuggestionType, SuggestionStatus
from backend.models.approved_explanation import ApprovedExplanation, ApprovedExplanationSource
from backend.models.budget_line import BudgetLine
from backend.utils.auth_guards import require_login, require_admin, require_employee
from backend.services.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])


# Pydantic schemas
class SuggestionCreate(BaseModel):
    """Schema for creating a new suggestion."""
    budget_line_id: int
    municipality_id: int
    month: str  # YYYY-MM
    topic_code: str
    suggestion_type: str  # "preset" or "custom"
    preset_id: Optional[int] = None
    custom_text: Optional[str] = None


class SuggestionApprove(BaseModel):
    """Schema for approving a suggestion."""
    review_note: Optional[str] = None  # Optional note


class SuggestionReject(BaseModel):
    """Schema for rejecting a suggestion."""
    review_note: str  # Required reason for rejection


class SuggestionResponse(BaseModel):
    """Response schema for a suggestion."""
    id: int
    budget_line_id: int
    municipality_id: int
    month: str
    topic_code: str
    suggestion_type: str
    preset_id: Optional[int] = None
    custom_text: Optional[str] = None
    suggested_by: int
    status: str
    reviewed_by: Optional[int] = None
    review_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SuggestionDetailResponse(SuggestionResponse):
    """Extended response with related data."""
    suggester_name: Optional[str] = None
    reviewer_name: Optional[str] = None
    preset_text: Optional[str] = None


class RejectedSuggestionResponse(BaseModel):
    """Response schema for rejected suggestions (for employees)."""
    id: int
    municipality_name: Optional[str] = None
    month: str
    topic_code: str
    budget_line_name: Optional[str] = None
    custom_text: Optional[str] = None
    preset_text: Optional[str] = None
    review_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    suggestion_type: str
    preset_id: Optional[int] = None


# ===== POST ENDPOINTS =====

@router.post("", response_model=SuggestionResponse, status_code=status.HTTP_201_CREATED)
async def submit_suggestion(
    data: SuggestionCreate,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    """
    Submit a new explanation suggestion.
    
    Only employees (and admins) can submit suggestions.
    Employees can only suggest for municipalities they're assigned to.
    """
    # Verify user is employee or admin
    if current_user.role not in [UserRole.ADMIN, UserRole.EMPLOYEE]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employees and admins can submit suggestions"
        )
    
    # Verify employee is assigned to this municipality
    if current_user.role == UserRole.EMPLOYEE:
        assigned = any(m.id == data.municipality_id for m in current_user.municipalities_assigned)
        if not assigned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this municipality"
            )
    
    # Verify budget line exists
    budget_line = db.query(BudgetLine).filter(BudgetLine.id == data.budget_line_id).first()
    if not budget_line:
        raise HTTPException(status_code=404, detail="Budget line not found")
    
    # Create suggestion
    suggestion = ExplanationSuggestion(
        budget_line_id=data.budget_line_id,
        municipality_id=data.municipality_id,
        month=data.month,
        topic_code=data.topic_code,
        suggestion_type=data.suggestion_type,
        preset_id=data.preset_id if data.suggestion_type == "preset" else None,
        custom_text=data.custom_text if data.suggestion_type == "custom" else None,
        suggested_by=current_user.id,
        status=SuggestionStatus.PENDING
    )
    
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    
    logger.info(f"Suggestion submitted by {current_user.email} for month {data.month} code {data.topic_code}")
    
    return suggestion


# ===== GET ENDPOINTS =====

@router.get("/pending", response_model=List[SuggestionDetailResponse])
async def get_pending_suggestions(
    municipality_id: Optional[int] = Query(None),
    employee_id: Optional[int] = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get pending suggestions (admin only).
    
    Query params:
    - municipality_id: Filter by municipality
    - employee_id: Filter by employee who submitted
    """
    logger.info(f"🔍 GET /api/suggestions/pending called by admin {current_user.email}")
    logger.info(f"   Current user role: {current_user.role}")
    
    query = db.query(ExplanationSuggestion).filter(
        ExplanationSuggestion.status == SuggestionStatus.PENDING
    )
    
    if municipality_id:
        query = query.filter(ExplanationSuggestion.municipality_id == municipality_id)
    
    if employee_id:
        query = query.filter(ExplanationSuggestion.suggested_by == employee_id)
    
    suggestions = query.order_by(ExplanationSuggestion.created_at.desc()).all()
    logger.info(f"   Found {len(suggestions)} pending suggestions")
    
    # Enrich with related data
    result = []
    for s in suggestions:
        try:
            # Build enriched data
            suggester_name = ""
            if s.suggester:
                suggester_name = f"{s.suggester.first_name or ''} {s.suggester.last_name or ''}".strip()
            suggester_name = suggester_name or "Unknown"
            
            reviewer_name = None
            if s.reviewer:
                reviewer_name = f"{s.reviewer.first_name or ''} {s.reviewer.last_name or ''}".strip()
            
            preset_text = None
            if s.preset:
                preset_text = s.preset.preset_text
            
            # Create response object
            detail = SuggestionDetailResponse(
                id=s.id,
                budget_line_id=s.budget_line_id,
                municipality_id=s.municipality_id,
                month=s.month,
                topic_code=s.topic_code,
                suggestion_type=s.suggestion_type,
                preset_id=s.preset_id,
                custom_text=s.custom_text,
                suggested_by=s.suggested_by,
                status=s.status,
                reviewed_by=s.reviewed_by,
                review_note=s.review_note,
                created_at=s.created_at,
                updated_at=s.updated_at,
                suggester_name=suggester_name,
                reviewer_name=reviewer_name,
                preset_text=preset_text
            )
            logger.info(f"   Suggestion {s.id}: type={s.suggestion_type}, status={s.status}, by={suggester_name}, custom_text={'✓' if s.custom_text else '✗'}")
            result.append(detail)
        except Exception as e:
            logger.error(f"   Error processing suggestion {s.id}: {str(e)}", exc_info=True)
            raise
    
    logger.info(f"   Returning {len(result)} suggestions to {current_user.email}")
    return result


@router.get("/pending/count")
async def get_pending_suggestions_count(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get count of pending suggestions (admin only).
    Returns: { "count": N }
    """
    logger.info(f"🔍 GET /api/suggestions/pending/count called by admin {current_user.email}")
    
    count = db.query(ExplanationSuggestion).filter(
        ExplanationSuggestion.status == SuggestionStatus.PENDING
    ).count()
    
    logger.info(f"   Pending count: {count}")
    return {"count": count}


@router.get("/my", response_model=List[SuggestionDetailResponse])
async def get_my_suggestions(
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    """
    Get suggestions submitted by the current user.
    
    Employees see only their own suggestions.
    Admins receive an empty list (use /pending instead).
    """
    if current_user.role == UserRole.ADMIN:
        return []
    
    suggestions = db.query(ExplanationSuggestion).filter(
        ExplanationSuggestion.suggested_by == current_user.id
    ).order_by(
        ExplanationSuggestion.created_at.desc()
    ).all()
    
    # Enrich with related data
    result = []
    for s in suggestions:
        detail = SuggestionDetailResponse.from_orm(s)
        if s.reviewer:
            detail.reviewer_name = f"{s.reviewer.first_name} {s.reviewer.last_name}".strip()
        if s.preset:
            detail.preset_text = s.preset.preset_text
        result.append(detail)
    
    return result


@router.get("/my-rejected", response_model=List[RejectedSuggestionResponse])
async def get_my_rejected_suggestions(
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    """
    Get all rejected suggestions for the current employee user.
    
    Returns:
    - List of rejected suggestions with municipality name, budget line name, and rejection reason
    - Empty list for non-employee users
    """
    if current_user.role not in [UserRole.EMPLOYEE, UserRole.ADMIN]:
        return []
    
    # Query all REJECTED suggestions by current user
    suggestions = db.query(ExplanationSuggestion).filter(
        ExplanationSuggestion.suggested_by == current_user.id,
        ExplanationSuggestion.status == SuggestionStatus.REJECTED
    ).order_by(
        ExplanationSuggestion.created_at.desc()
    ).all()
    
    # Enrich with related data
    result = []
    for s in suggestions:
        municipality_name = None
        budget_line_name = None
        preset_text = None
        
        # Get municipality name
        if s.municipality:
            municipality_name = s.municipality.name
        
        # Get budget line name
        if s.budget_line:
            budget_line_name = s.budget_line.budget_topic or f"Code {s.topic_code}"
        
        # Get preset text if applicable
        if s.preset:
            preset_text = s.preset.preset_text
        
        detail = RejectedSuggestionResponse(
            id=s.id,
            municipality_name=municipality_name,
            month=s.month,
            topic_code=s.topic_code,
            budget_line_name=budget_line_name,
            custom_text=s.custom_text,
            preset_text=preset_text,
            review_note=s.review_note,
            created_at=s.created_at,
            updated_at=s.updated_at,
            suggestion_type=s.suggestion_type,
            preset_id=s.preset_id
        )
        result.append(detail)
    
    logger.info(f"Employee {current_user.email} fetched {len(result)} rejected suggestions")
    return result


@router.get("/my-counts")
async def get_my_suggestion_counts(
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    """
    Get counts of the current employee's suggestions by status.
    Returns: { "pending": N, "approved": N, "rejected": N }
    Non-employees always get zeros.
    """
    if current_user.role not in [UserRole.EMPLOYEE, UserRole.ADMIN]:
        return {"pending": 0, "approved": 0, "rejected": 0}

    base = db.query(ExplanationSuggestion).filter(
        ExplanationSuggestion.suggested_by == current_user.id
    )
    pending = base.filter(ExplanationSuggestion.status == SuggestionStatus.PENDING).count()
    approved = base.filter(ExplanationSuggestion.status == SuggestionStatus.APPROVED).count()
    rejected = base.filter(ExplanationSuggestion.status == SuggestionStatus.REJECTED).count()

    return {"pending": pending, "approved": approved, "rejected": rejected}


class EmployeeSuggestionResponse(BaseModel):
    """Enriched suggestion response for the employee's own suggestions page."""
    id: int
    municipality_name: Optional[str] = None
    budget_line_name: Optional[str] = None
    month: str
    topic_code: str
    suggestion_type: str
    custom_text: Optional[str] = None
    preset_text: Optional[str] = None
    status: str
    review_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # for resubmit
    budget_line_id: int
    municipality_id: int
    preset_id: Optional[int] = None

    class Config:
        from_attributes = True


@router.get("/my-all", response_model=List[EmployeeSuggestionResponse])
async def get_my_all_suggestions(
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    """
    Get ALL suggestions by the current employee (pending, approved, rejected).
    Non-employees get an empty list.
    """
    if current_user.role not in [UserRole.EMPLOYEE, UserRole.ADMIN]:
        return []

    suggestions = db.query(ExplanationSuggestion).filter(
        ExplanationSuggestion.suggested_by == current_user.id
    ).order_by(ExplanationSuggestion.created_at.desc()).all()

    result = []
    for s in suggestions:
        result.append(EmployeeSuggestionResponse(
            id=s.id,
            municipality_name=s.municipality.name if s.municipality else None,
            budget_line_name=(s.budget_line.budget_topic if s.budget_line else None) or f"קוד {s.topic_code}",
            month=s.month,
            topic_code=s.topic_code,
            suggestion_type=s.suggestion_type,
            custom_text=s.custom_text,
            preset_text=s.preset.preset_text if s.preset else None,
            status=str(s.status.value) if hasattr(s.status, 'value') else str(s.status),
            review_note=s.review_note,
            created_at=s.created_at,
            updated_at=s.updated_at,
            budget_line_id=s.budget_line_id,
            municipality_id=s.municipality_id,
            preset_id=s.preset_id,
        ))

    return result


# ===== PATCH ENDPOINTS =====

@router.patch("/{suggestion_id}/approve", response_model=SuggestionResponse)
async def approve_suggestion(
    suggestion_id: int,
    data: SuggestionApprove,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Approve a suggestion and make it the official explanation (admin only).
    
    This creates an ApprovedExplanation record that municipalities will see.
    """
    suggestion = db.query(ExplanationSuggestion).filter(
        ExplanationSuggestion.id == suggestion_id
    ).first()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    if suggestion.status != SuggestionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only approve pending suggestions, this is {suggestion.status}"
        )
    
    # Determine the final text
    if suggestion.suggestion_type == "preset" and suggestion.preset:
        final_text = suggestion.preset.preset_text
    else:
        final_text = suggestion.custom_text
    
    # Validate final_text is not empty
    if not final_text or not final_text.strip():
        logger.error(f"Cannot approve suggestion {suggestion_id}: final_text is empty. type={suggestion.suggestion_type}, custom={suggestion.custom_text}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot approve: suggestion has no text content"
        )
    
    # Update suggestion
    suggestion.status = SuggestionStatus.APPROVED
    suggestion.reviewed_by = current_user.id
    suggestion.review_note = data.review_note
    
    try:
        # Create approved explanation record
        approved = ApprovedExplanation(
            budget_line_id=suggestion.budget_line_id,
            municipality_id=suggestion.municipality_id,
            month=suggestion.month,
            topic_code=suggestion.topic_code,
            final_text=final_text,
            approved_by=current_user.id,
            source=ApprovedExplanationSource.SUGGESTION,
            suggestion_id=suggestion.id
        )
        
        db.add(approved)
        db.commit()
        db.refresh(suggestion)
        logger.info(f"✅ Suggestion {suggestion_id} approved by {current_user.email}, ApprovedExplanation created")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error creating ApprovedExplanation for suggestion {suggestion_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating approved explanation: {str(e)}"
        )
    
    logger.info(f"Suggestion {suggestion_id} approved by {current_user.email}")
    
    return suggestion


@router.patch("/{suggestion_id}/reject", response_model=SuggestionResponse)
async def reject_suggestion(
    suggestion_id: int,
    data: SuggestionReject,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Reject a suggestion with a reason (admin only).
    
    The employee can see the reason and revise their suggestion.
    """
    suggestion = db.query(ExplanationSuggestion).filter(
        ExplanationSuggestion.id == suggestion_id
    ).first()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    if suggestion.status != SuggestionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only reject pending suggestions, this is {suggestion.status}"
        )
    
    suggestion.status = SuggestionStatus.REJECTED
    suggestion.reviewed_by = current_user.id
    suggestion.review_note = data.review_note
    
    db.commit()
    db.refresh(suggestion)
    
    logger.info(f"Suggestion {suggestion_id} rejected by {current_user.email}: {data.review_note}")
    
    return suggestion
