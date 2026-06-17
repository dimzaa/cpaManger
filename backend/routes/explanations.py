"""
Explanations Routes

API endpoints for:
1. Getting auto-generated explanations with change detection
2. Creating/updating custom explanation overrides (CPA admin only)
3. Deleting custom explanations

Supports REAL Ministry budget codes: 3, 19, 33, 50, 47, 5
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import logging

from backend.database import get_db
from backend.models.custom_explanation import CustomExplanation
from backend.models.approved_explanation import ApprovedExplanation
from backend.models.user import User
from backend.models.municipality import Municipality
from backend.models.monthly_run import MonthlyRun
from backend.models.budget_line import BudgetLine
from backend.utils.auth_guards import require_login, require_admin
from backend.services.explanation_service import get_explanation
from backend.services.smart_explanation_real import SmartExplanationEngine
from backend.services.change_detector import ChangeDetector
from backend.data.purple_booklet_rules import get_budget_topic

logger = logging.getLogger(__name__)

# Pydantic schemas
class ExplanationCreate(BaseModel):
    custom_text: str


class ExplanationResponse(BaseModel):
    id: int
    municipality_id: int
    month: str
    topic_code: str
    custom_text: str


class ExplanationDetail(BaseModel):
    topic_code: str
    topic_name: str
    explanation: str
    is_custom: bool
    has_changes: bool
    changes: List[dict] = []
    financial_impact: str
    amount: float


class ExplanationsMonthResponse(BaseModel):
    municipality_id: int
    month: str
    explanations: List[ExplanationDetail]


# Create router
router = APIRouter(prefix="/api/explanations", tags=["explanations"])


@router.get("/{municipality_id}/{month}/{topic_code}")
async def get_explanation_detail(
    municipality_id: int,
    month: str,
    topic_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
) -> dict:
    """
    Get detailed explanation for a budget line with change detection.
    
    Includes:
    - Auto-generated explanation from templates
    - Changes detected from previous month
    - Custom override if CPA created one
    - Financial impact analysis
    
    Returns:
        {
            "explanation": "Hebrew explanation text",
            "is_custom": bool,
            "is_retro": bool,
            "has_changes": bool,
            "changes": [list of detected changes],
            "topic_name": "שכל\"מ גנ'י",
            "financial_impact": "₪50,000",
            "municipality_id": int,
            "month": str,
            "topic_code": str,
        }
    """
    
    try:
        # Check municipality access
        municipality = db.query(Municipality).filter(
            Municipality.id == municipality_id
        ).first()
        
        if not municipality:
            raise HTTPException(status_code=404, detail="Municipality not found")
        
        # Verify user has access
        if current_user.role == "municipality" and current_user.municipality_id != municipality_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get current month's budget line
        current_run = db.query(MonthlyRun).filter(
            MonthlyRun.municipality_id == municipality_id,
            MonthlyRun.month == month,
        ).first()
        
        if not current_run:
            raise HTTPException(status_code=404, detail="No budget data for this month")
        
        current_line = db.query(BudgetLine).filter(
            BudgetLine.run_id == current_run.id,
            BudgetLine.topic_code == topic_code,
        ).first()
        
        if not current_line:
            raise HTTPException(status_code=404, detail="No budget line for this topic")
        
        # Get previous month's budget line for change detection
        previous_line = None
        previous_run = db.query(MonthlyRun).filter(
            MonthlyRun.municipality_id == municipality_id,
            MonthlyRun.month < month,
        ).order_by(MonthlyRun.month.desc()).first()
        
        if previous_run:
            previous_line = db.query(BudgetLine).filter(
                BudgetLine.run_id == previous_run.id,
                BudgetLine.topic_code == topic_code,
            ).first()
        
        # Check for custom explanation override
        custom = db.query(CustomExplanation).filter(
            CustomExplanation.municipality_id == municipality_id,
            CustomExplanation.month == month,
            CustomExplanation.topic_code == topic_code,
        ).first()
        
        # Get topic info
        topic = get_budget_topic(topic_code)
        topic_name = topic.get("name", "") if topic else ""
        
        # If custom explanation exists, return it (with basic formatting)
        if custom:
            return {
                "smart_explanation": None,  # No smart breakdown for custom
                "custom_text": custom.custom_text,
                "is_custom": True,
                "municipality_id": municipality_id,
                "month": month,
                "topic_code": topic_code,
                "topic_name": topic_name,
            }
        
        # Convert budget lines to dicts for SmartExplanationEngine
        current_line_dict = current_line.__dict__.copy()
        previous_line_dict = previous_line.__dict__.copy() if previous_line else None
        
        # Generate smart explanation with formula breakdown and change detection
        smart_explanation = SmartExplanationEngine.generate_explanation(
            current_line_dict,
            previous_line=previous_line_dict
        )
        
        return {
            "smart_explanation": smart_explanation,
            "is_custom": False,
            "municipality_id": municipality_id,
            "month": month,
            "topic_code": topic_code,
            "topic_name": topic_name,
            "amount": float(current_line.amount or 0),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting explanation: {e}")
        raise HTTPException(status_code=500, detail="Error generating explanation")


@router.get("/municipality/{municipality_id}/month/{month}")
async def get_all_explanations_for_month(
    municipality_id: int,
    month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
) -> ExplanationsMonthResponse:
    """
    Get all explanations for all topics in a given month.
    
    Returns all budget lines with their explanations, changes, and financial impact.
    
    Returns:
        {
            "municipality_id": int,
            "month": str,
            "explanations": [
                {
                    "topic_code": "3",
                    "topic_name": "שכל\"מ גנ'י",
                    "explanation": "...",
                    "is_custom": bool,
                    "has_changes": bool,
                    "changes": [...],
                    "financial_impact": "₪X,XXX",
                    "amount": float,
                },
                ...
            ]
        }
    """
    
    try:
        # Check municipality access
        municipality = db.query(Municipality).filter(
            Municipality.id == municipality_id
        ).first()
        
        if not municipality:
            raise HTTPException(status_code=404, detail="Municipality not found")
        
        if current_user.role == "municipality" and current_user.municipality_id != municipality_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get current month's budget lines
        current_run = db.query(MonthlyRun).filter(
            MonthlyRun.municipality_id == municipality_id,
            MonthlyRun.month == month,
        ).first()
        
        if not current_run:
            raise HTTPException(status_code=404, detail="No budget data for this month")
        
        budget_lines = db.query(BudgetLine).filter(
            BudgetLine.run_id == current_run.id,
        ).all()
        
        # Get previous month for change detection
        previous_run = db.query(MonthlyRun).filter(
            MonthlyRun.municipality_id == municipality_id,
            MonthlyRun.month < month,
        ).order_by(MonthlyRun.month.desc()).first()
        
        explanations = []
        
        for line in budget_lines:
            # Get previous line for change detection
            previous_line = None
            if previous_run:
                previous_line = db.query(BudgetLine).filter(
                    BudgetLine.run_id == previous_run.id,
                    BudgetLine.topic_code == line.topic_code,
                ).first()
            
            # Get custom explanation if exists (CPA-created override)
            custom = db.query(CustomExplanation).filter(
                CustomExplanation.municipality_id == municipality_id,
                CustomExplanation.month == month,
                CustomExplanation.topic_code == line.topic_code,
            ).first()
            
            # Get approved explanation if exists (from approved suggestion)
            approved = db.query(ApprovedExplanation).filter(
                ApprovedExplanation.municipality_id == municipality_id,
                ApprovedExplanation.month == month,
                ApprovedExplanation.topic_code == line.topic_code,
            ).first()
            
            # Use approved explanation if available, otherwise use custom
            explanation_override = custom or approved
            
            # Generate explanation
            explanation_result = get_explanation(
                line,
                previous_line=previous_line,
                custom_explanation=explanation_override
            )
            
            topic = get_budget_topic(line.topic_code)
            topic_name = topic.get("name", "") if topic else ""
            
            # Calculate changes and impact
            changes = []
            financial_impact = "₪0"
            if previous_line and not explanation_override:
                detector = ChangeDetector()
                detected_changes = detector.detect_changes(
                    previous_line.__dict__,
                    line.__dict__,
                    line.topic_code
                )
                changes = [change.to_dict() for change in detected_changes]
                
                total = float(line.amount or 0)
                for change in detected_changes:
                    if change.impact_amount:
                        total += change.impact_amount
                if total != 0:
                    financial_impact = f"₪{total:,.2f}"
            else:
                total = float(line.amount or 0)
                if total != 0:
                    financial_impact = f"₪{total:,.2f}"
            
            explanations.append(ExplanationDetail(
                topic_code=line.topic_code,
                topic_name=topic_name,
                explanation=explanation_result["text"],
                is_custom=explanation_result["is_custom"],
                has_changes=explanation_result.get("has_changes", False),
                changes=changes,
                financial_impact=financial_impact,
                amount=float(line.amount or 0),
            ))
        
        return ExplanationsMonthResponse(
            municipality_id=municipality_id,
            month=month,
            explanations=explanations,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting month explanations: {e}")
        raise HTTPException(status_code=500, detail="Error generating explanations")


@router.post("/{municipality_id}/{month}/{topic_code}", response_model=ExplanationResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_explanation(
    municipality_id: int,
    month: str,
    topic_code: str,
    data: ExplanationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Create or update a custom explanation for a budget line.
    
    CPA admin only. Creates an override that replaces auto-generated explanation.
    
    Args:
        custom_text: The Hebrew explanation text written by admin
    
    Returns:
        The created/updated CustomExplanation
    """
    
    try:
        logger.info(f"📝 POST /api/explanations/{municipality_id}/{month}/{topic_code}")
        logger.info(f"   User: {current_user.email} (role: {current_user.role})")
        logger.info(f"   Text length: {len(data.custom_text)} chars")
        
        # Verify user has access to this municipality
        # CPA admins (role "admin") can edit any municipality
        # Municipality users can only edit their own
        if current_user.role == "municipality" and current_user.municipality_id != municipality_id:
            logger.warning(f"   ❌ Access denied: user municipality {current_user.municipality_id} != {municipality_id}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Find existing explanation
        explanation = db.query(CustomExplanation).filter(
            CustomExplanation.municipality_id == municipality_id,
            CustomExplanation.month == month,
            CustomExplanation.topic_code == topic_code,
        ).first()
        
        if explanation:
            # Update existing
            logger.info(f"   ✏️ Updating existing explanation (id: {explanation.id})")
            explanation.custom_text = data.custom_text
        else:
            # Create new
            logger.info(f"   ✨ Creating new explanation")
            explanation = CustomExplanation(
                municipality_id=municipality_id,
                month=month,
                topic_code=topic_code,
                custom_text=data.custom_text,
            )
        
        db.add(explanation)
        db.commit()
        db.refresh(explanation)
        
        logger.info(f"   ✅ Success: explanation {explanation.id} saved")
        return explanation
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating/updating explanation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error saving explanation")


@router.delete("/{municipality_id}/{month}/{topic_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_explanation(
    municipality_id: int,
    month: str,
    topic_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Delete a custom explanation (reverts to auto-generated).
    
    CPA admin only.
    """
    
    try:
        # Verify admin access (only admins can delete; municipality users cannot)
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Find and delete
        explanation = db.query(CustomExplanation).filter(
            CustomExplanation.municipality_id == municipality_id,
            CustomExplanation.month == month,
            CustomExplanation.topic_code == topic_code,
        ).first()
        
        if explanation:
            db.delete(explanation)
            db.commit()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting explanation: {e}")
        raise HTTPException(status_code=500, detail="Error deleting explanation")
