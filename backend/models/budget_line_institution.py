from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from backend.database import Base


class BudgetLineInstitution(Base):
    __tablename__ = "budget_line_institutions"

    id = Column(Integer, primary_key=True, index=True)
    budget_line_id = Column(
        Integer,
        ForeignKey("budget_lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_code = Column(String(32), nullable=False, index=True)
    institution_name = Column(String(255), nullable=True)
    amount = Column(Float, nullable=False)
    num_children = Column(Integer, nullable=True)
    participation_pct = Column(Float, nullable=True)
    source_file = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    budget_line = relationship("BudgetLine", back_populates="institution_breakdown")
