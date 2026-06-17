"""
Preset Explanations Routes

Admin endpoints for managing preset explanation templates.
Employees choose from presets when submitting suggestions.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from backend.database import get_db
from backend.models.user import User, UserRole
from backend.models.preset_explanation import PresetExplanation
from backend.utils.auth_guards import require_login, require_admin

router = APIRouter(prefix="/api/presets", tags=["presets"])


# Pydantic schemas
class PresetCreate(BaseModel):
    """Schema for creating a new preset explanation."""
    topic_code: str  # "3", "19", "33", "45", "47", "general"
    preset_text: str  # Hebrew text
    category: str  # "retro", "increase", "decrease", "correction", "new_position", "other"


class PresetUpdate(BaseModel):
    """Schema for updating a preset."""
    preset_text: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None


class PresetResponse(BaseModel):
    """Response schema for a preset."""
    id: int
    topic_code: str
    preset_text: str
    category: str
    is_active: bool
    created_by: int

    class Config:
        from_attributes = True


# ===== GET ENDPOINTS =====

@router.get("", response_model=List[PresetResponse])
def get_presets(
    topic_code: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get preset explanations.
    
    Query params:
    - topic_code: Filter by budget code (e.g., "3", "19", "general")
    - active_only: Only return active presets (default: True)
    """
    query = db.query(PresetExplanation)
    
    if active_only:
        query = query.filter(PresetExplanation.is_active == True)
    
    if topic_code:
        query = query.filter(PresetExplanation.topic_code == topic_code)
    
    return query.order_by(PresetExplanation.topic_code, PresetExplanation.id).all()


# ===== POST ENDPOINTS =====

@router.post("", response_model=PresetResponse, status_code=status.HTTP_201_CREATED)
def create_preset(
    data: PresetCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new preset explanation (admin only).
    """
    preset = PresetExplanation(
        topic_code=data.topic_code,
        preset_text=data.preset_text,
        category=data.category,
        created_by=current_user.id,
        is_active=True
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset


# ===== PATCH ENDPOINTS =====

@router.patch("/{preset_id}", response_model=PresetResponse)
def update_preset(
    preset_id: int,
    data: PresetUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update a preset explanation (admin only).
    """
    preset = db.query(PresetExplanation).filter(PresetExplanation.id == preset_id).first()
    
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    if data.preset_text is not None:
        preset.preset_text = data.preset_text
    if data.category is not None:
        preset.category = data.category
    if data.is_active is not None:
        preset.is_active = data.is_active
    
    db.commit()
    db.refresh(preset)
    return preset


# ===== DELETE ENDPOINTS =====

@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preset(
    preset_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a preset explanation (admin only).
    """
    preset = db.query(PresetExplanation).filter(PresetExplanation.id == preset_id).first()
    
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    db.delete(preset)
    db.commit()
    return None
