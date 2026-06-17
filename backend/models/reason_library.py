from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ARRAY
from sqlalchemy.sql import func
from backend.database import Base


class ReasonLibrary(Base):
    """
    Reasons Library — A searchable, categorized database of all possible 
    reasons for budget changes. Provides templates for both employees 
    (suggesting reasons) and auto-generation of explanations.
    """
    __tablename__ = "reasons_library"

    id = Column(Integer, primary_key=True)
    
    # Unique identifier for this reason
    code = Column(String(50), unique=True, nullable=False, index=True)
    
    # Which budget codes this reason applies to
    # Examples: ["3"], ["19"], ["3", "19", "33"], ["all"]
    topic_codes = Column(JSON, nullable=False, default=list)
    
    # Category for grouping and filtering
    # ילדים, משרות, שכר, גן, רטרו, תיקון, מדיניות, משפטי, אחר
    category = Column(String(50), nullable=False, index=True)
    
    # Short title shown in list (Hebrew)
    title_hebrew = Column(String(200), nullable=False)
    
    # Full explanation template (Hebrew) — can include {placeholders}
    # Placeholders: {period_month}, {count}, {detail_value}, etc.
    explanation_template = Column(Text, nullable=False)
    
    # Direction: indicates if this increases, decreases, or neutrally affects amounts
    # Used for smart filtering: if amount went UP, show "increase" reasons first
    # "increase" | "decrease" | "neutral"
    direction = Column(String(20), nullable=False, default="neutral", index=True)
    
    # Severity level — helps CPA prioritize
    # "routine" = normal expected change (green badge)
    # "attention" = CPA should verify (amber badge)
    # "urgent" = needs immediate action (red badge)
    severity = Column(String(20), nullable=False, default="routine", index=True)
    
    # If true, employee must provide additional data when selecting this reason
    requires_detail = Column(Boolean, nullable=False, default=False)
    
    # Prompt text for the additional detail input (Hebrew)
    # Example: "כמה ילדים נוספו/עזבו?"
    detail_prompt = Column(String(200), nullable=True)
    
    # Soft delete flag and active status
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    # Display order within category
    sort_order = Column(Integer, nullable=False, default=999)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def to_dict(self, include_template=True):
        """Convert to dict for API responses"""
        return {
            "id": self.id,
            "code": self.code,
            "topic_codes": self.topic_codes,
            "category": self.category,
            "title_hebrew": self.title_hebrew,
            "explanation_template": self.explanation_template if include_template else None,
            "direction": self.direction,
            "severity": self.severity,
            "requires_detail": self.requires_detail,
            "detail_prompt": self.detail_prompt,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
