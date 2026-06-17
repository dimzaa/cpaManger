"""
SQLAlchemy model for custom_explanations table.

Stores manually-written explanations that CPA writes for specific budget lines.
These override the auto-generated explanations.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class CustomExplanation(Base):
    """
    Stores a manually-written explanation for a budget line.
    
    CPA can override the auto-generated explanation with his own wording.
    
    Attributes:
        id: Primary key
        municipality_id: Foreign key to Municipality
        month: Month in YYYY-MM format
        topic_code: Budget topic code (e.g., "101")
        custom_text: The custom explanation text written by CPA
        created_at: When the custom explanation was created
        updated_at: When it was last updated
        municipality: Relationship to Municipality
    """
    __tablename__ = "custom_explanations"
    
    id = Column(Integer, primary_key=True, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=False, index=True)
    month = Column(String(7), nullable=False, index=True)  # YYYY-MM format
    topic_code = Column(String(10), nullable=False, index=True)
    custom_text = Column(String(1000), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationship to Municipality
    municipality = relationship("Municipality", back_populates="custom_explanations")
    
    def __repr__(self):
        return f"<CustomExplanation(municipality_id={self.municipality_id}, month={self.month}, topic_code={self.topic_code})>"
