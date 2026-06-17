"""
Explanation suggestions — employee proposals for budget line explanations pending CPA approval.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum

from backend.database import Base


class SuggestionStatus(str, PyEnum):
    """Status of an explanation suggestion."""
    PENDING = "pending"  # Awaiting CPA review
    APPROVED = "approved"  # CPA approved, now shown to municipality
    REJECTED = "rejected"  # CPA rejected, employee can revise


class SuggestionType(str, PyEnum):
    """Type of suggestion."""
    PRESET = "preset"  # Using a preset explanation
    CUSTOM = "custom"  # Custom written explanation


class ExplanationSuggestion(Base):
    """
    Represents an employee's suggestion for a budget line explanation.
    
    Attributes:
        id: Primary key
        budget_line_id: Which budget line this suggestion is for
        municipality_id: Which municipality's budget
        month: Month in YYYY-MM format
        topic_code: Budget code (e.g., "3", "19")
        suggestion_type: "preset" (chosen from list) or "custom" (written by employee)
        preset_id: ID of preset if suggestion_type="preset"
        custom_text: Employee's custom text if suggestion_type="custom"
        suggested_by: ID of employee who made the suggestion
        status: pending, approved, or rejected
        reviewed_by: ID of CPA who reviewed (if approved/rejected)
        review_note: CPA's rejection reason (if rejected)
        created_at: When suggestion was submitted
        updated_at: Last modification time
    """
    __tablename__ = "explanation_suggestions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # What is this for?
    budget_line_id = Column(Integer, ForeignKey("budget_lines.id"), nullable=False, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=False, index=True)
    month = Column(String(7), nullable=False, index=True)  # YYYY-MM format
    topic_code = Column(String(10), nullable=False)  # e.g., "3", "19"
    
    # What type of suggestion?
    suggestion_type = Column(String(20), nullable=False)  # "preset" or "custom"
    preset_id = Column(Integer, ForeignKey("preset_explanations.id"), nullable=True)
    custom_text = Column(String(500), nullable=True)
    
    # Who and when?
    suggested_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), default=SuggestionStatus.PENDING, nullable=False, index=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_note = Column(String(500), nullable=True)  # Rejection reason or other notes
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    budget_line = relationship("BudgetLine", foreign_keys=[budget_line_id], backref="suggestions")
    municipality = relationship("Municipality", foreign_keys=[municipality_id], backref="suggestions")
    suggester = relationship("User", foreign_keys=[suggested_by], backref="suggestions_made")
    reviewer = relationship("User", foreign_keys=[reviewed_by], backref="suggestions_reviewed")
    preset = relationship("PresetExplanation", foreign_keys=[preset_id])
