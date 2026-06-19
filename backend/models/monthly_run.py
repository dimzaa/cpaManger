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
    """
    __tablename__ = "monthly_runs"

    id = Column(Integer, primary_key=True, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=False, index=True)
    month = Column(String(7), nullable=False)
    year = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, server_default=func.now())
    file_name = Column(String(255), nullable=True)

    status = Column(String(20), default="pending")

    # Cross-reference data
    invoice_total = Column(Float, nullable=True)
    breakdown_total = Column(Float, nullable=True)
    is_balanced = Column(Boolean, default=False)
    difference = Column(Float, nullable=True)
    error_message = Column(String(500), nullable=True)

    # Priority-1 dashboard aggregates (computed at upload time).
    # Sourced from budget_lines.amount + is_retro for this run.
    # Denormalised so the dashboard / muni portal render KPI cards via a
    # single SELECT on monthly_runs without scanning budget_lines.
    regular_total = Column(Float, nullable=True)
    retro_positive_total = Column(Float, nullable=True)
    retro_negative_total = Column(Float, nullable=True)
    topics_count = Column(Integer, nullable=True)
    lines_count = Column(Integer, nullable=True)

    # CPA review sign-off (separate from processing status)
    review_status = Column(String(20), nullable=False, default="pending", index=True)
    review_status_note = Column(String(1000), nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    reviewed_at = Column(DateTime, nullable=True)

    municipality = relationship("Municipality", back_populates="monthly_runs")
    budget_lines = relationship(
        "BudgetLine",
        back_populates="monthly_run",
        cascade="all, delete-orphan"
    )
    reviewer = relationship("User", foreign_keys=[reviewed_by_user_id])

    def __repr__(self):
        return f"<MonthlyRun id={self.id} mun_id={self.municipality_id} month={self.month} balanced={self.is_balanced}>"
