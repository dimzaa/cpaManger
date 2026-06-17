"""
SQLAlchemy model for municipalities table.

Stores information about each municipality (city/town)
that the CPA manages.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class Municipality(Base):
    """
    Represents a municipality (city/town) that the CPA manages.
    
    Attributes:
        id: Primary key
        name: Hebrew name of the municipality (e.g., "עיריית נצרת")
        code: Ministry's internal code (e.g., "3000")
        login_email: Email for portal access
        created_at: When the record was created
        monthly_runs: Relationship to MonthlyRun records
        budget_lines: Relationship to BudgetLine records
    """
    __tablename__ = "municipalities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # Hebrew name
    code = Column(String(10), nullable=False, unique=True, index=True)  # Ministry code
    login_email = Column(String(255), nullable=True)  # For portal access
    is_test = Column(Boolean, default=False, index=True)  # Flag for test/demo data
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    monthly_runs = relationship(
        "MonthlyRun",
        back_populates="municipality",
        cascade="all, delete-orphan"
    )
    budget_lines = relationship(
        "BudgetLine",
        back_populates="municipality",
        cascade="all, delete-orphan"
    )
    custom_explanations = relationship(
        "CustomExplanation",
        back_populates="municipality",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Municipality id={self.id} code={self.code} name={self.name}>"
