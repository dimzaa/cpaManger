"""
Preset explanations — reusable explanation templates for different budget scenarios.

CPA admins create these, employees select from them, or customize.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class PresetExplanation(Base):
    """
    Represents a preset explanation template that employees can use.
    
    Attributes:
        id: Primary key
        topic_code: Budget code this preset applies to (e.g., "3", "19", "33", or "general")
        preset_text: Hebrew explanation text
        category: Type of explanation (retro, increase, decrease, correction, new_position, other)
        created_by: ID of admin who created this preset
        is_active: Whether this preset is available for use
        created_at: When the preset was created
        updated_at: Last modification time
    """
    __tablename__ = "preset_explanations"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_code = Column(String(10), nullable=False, index=True)  # "3", "19", "33", "45", "47", "general"
    preset_text = Column(String(500), nullable=False)  # Hebrew explanation
    category = Column(String(50), nullable=False)  # retro, increase, decrease, correction, new_position, other
    
    # Audit trail
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by], backref="preset_explanations_created")
