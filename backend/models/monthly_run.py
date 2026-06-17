"""
SQLAlchemy model for monthly_runs table.

Represents each file upload event by the CPA.
Tracks the balance between invoice total and breakdown sum.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, func
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class MonthlyRun(Base):
    """
    Represents a single monthly file upload/processing event.
    
    Each time the CPA uploads files, a new MonthlyRun is created.
    Tracks the invoice total vs breakdown sum comparison.
    
    Attributes:
        id: Primary key
        municipality_id: Foreign key to Municipality
        month: Month in YYYY-MM format (e.g., "2024-03")
        year: Year as integer (e.g., 2024)
        uploaded_at: Timestamp of when files were uploaded
        file_name: Original ZIP filename
        status: pending / processed / error
        invoice_total: Total amount from invoice file
        breakdown_total: Sum of all breakdown amounts
        is_balanced: True if invoice_total == breakdown_total
        difference: invoice_total - breakdown_total
        error_message: If status is "error", explanation of what went wrong
        municipality: Relationship to Municipality
        budget_lines: Relationship to BudgetLine records
    """
    __tablename__ = "monthly_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=False, index=True)
    month = Column(String(7), nullable=False)  # YYYY-MM format
    year = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, server_default=func.now())
    file_name = Column(String(255), nullable=True)
    
    status = Column(String(20), default="pending")  # pending / processed / error
    
    # Cross-reference data
    invoice_total = Column(Float, nullable=True)
    breakdown_total = Column(Float, nullable=True)
    is_balanced = Column(Boolean, default=False)
    difference = Column(Float, nullable=True)
    error_message = Column(String(500), nullable=True)

    # CPA review sign-off (separate from processing status)
    review_status = Column(String(20), nullable=False, default="pending", index=True)
    review_status_note = Column(String(1000), nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    # Relationships
    municipality = relationship("Municipality", back_populates="monthly_runs")
    budget_lines = relationship(
        "BudgetLine",
        back_populates="monthly_run",
        cascade="all, delete-orphan"
    )
    reviewer = relationship("User", foreign_keys=[reviewed_by_user_id])
    
    def __repr__(self):
        return f"<MonthlyRun id={self.id} mun_id={self.municipality_id} month={self.month} balanced={self.is_balanced}>"
