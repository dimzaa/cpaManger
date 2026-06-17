"""
SQLAlchemy model for budget_lines table.

Represents individual budget items from the breakdown file.
One row per budget topic per municipality per monthly run.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class BudgetLine(Base):
    """
    Represents a single budget line item from the breakdown file.
    
    One row = one budget topic for one municipality in one monthly run.
    Example: "Kindergartens in Nazareth for March 2024 = 120,000 shekels"
    
    Attributes:
        id: Primary key
        run_id: Foreign key to MonthlyRun (which upload this came from)
        municipality_id: Foreign key to Municipality
        budget_topic: Hebrew name of the topic (e.g., "גני ילדים")
        topic_code: Code for the topic (e.g., "101")
        amount: Amount in shekels for this line
        period_month: חודש תחולה - which month this payment is FOR (in YYYY-MM format)
        current_month: חודש העלאה - which month this was PAID in (in YYYY-MM format)
        line_type: regular / retro / shortage / adjustment
        is_retro: True if period_month != current_month
        notes: Human-readable explanation (auto-generated)
        created_at: When the record was created
        monthly_run: Relationship to MonthlyRun
        municipality: Relationship to Municipality
    """
    __tablename__ = "budget_lines"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("monthly_runs.id"), nullable=False, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=False, index=True)
    
    # Budget topic information
    budget_topic = Column(String(255), nullable=False)  # Hebrew name (e.g., "גני ילדים")
    topic_code = Column(String(10), nullable=False)  # Numeric code (e.g., "101")
    
    # Amount and dates
    amount = Column(Float, nullable=False)
    period_month = Column(String(7), nullable=False)  # YYYY-MM: which month this is FOR
    current_month = Column(String(7), nullable=False)  # YYYY-MM: which month this was PAID in

    # Actual values from Ministry file (Hebrew columns)
    num_children = Column(Integer, nullable=True)     # מספר ילדים — actual children from file
    participation_pct = Column(Float, nullable=True)  # אחוז — participation percentage from file
    
    # Classification
    line_type = Column(String(20), default="regular")  # regular / retro / shortage / adjustment
    is_retro = Column(Boolean, default=False)  # True if period_month != current_month

    # Variance-driver classification from student-count delta engine.
    # One of: "student_count", "formula_or_rate", "mixed", or NULL when
    # there's no prior run, no pupil count, or no movement to classify.
    variance_driver = Column(String(20), nullable=True, index=True)

    # Explanation
    notes = Column(String(500), nullable=True)  # Human-readable explanation
    
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    monthly_run = relationship("MonthlyRun", back_populates="budget_lines")
    municipality = relationship("Municipality", back_populates="budget_lines")
    institution_breakdown = relationship(
        "BudgetLineInstitution",
        back_populates="budget_line",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self):
        return (
            f"<BudgetLine id={self.id} mun_id={self.municipality_id} "
            f"topic={self.topic_code} amount={self.amount}>"
        )
