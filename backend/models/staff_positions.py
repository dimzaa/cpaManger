"""
SQLAlchemy model for staff_positions table.

Stores per-institution × per-role × per-month FTE values from MISROT
(institution-scoped) and MISROTGY (village-scoped — kindergartens).

Examples:
  * scope='institution', institution_code='318188', role='מזכיר/ה', month=1, fte=0.21
  * scope='gy',          institution_code=None,    role='גננת-קיזוז', month=1, fte=-11.82
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from backend.database import Base


class StaffPosition(Base):
    __tablename__ = "staff_positions"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(
        Integer,
        ForeignKey("monthly_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    municipality_id = Column(
        Integer, ForeignKey("municipalities.id"), nullable=False, index=True
    )

    # 'institution' (MISROT) or 'gy' (MISROTGY, kindergarten-village-level)
    scope = Column(String(16), nullable=False, index=True)

    # For scope='institution': the school code. For scope='gy': NULL and
    # village_code carries the ישוב code instead.
    institution_code = Column(String(32), nullable=True, index=True)
    institution_name = Column(String(255), nullable=True)

    # For scope='gy': the ישוב code
    village_code = Column(String(32), nullable=True)
    village_name = Column(String(255), nullable=True)

    # Role (תאור תפקיד) and its assignment category (שיוך תפקיד)
    role = Column(String(100), nullable=False)
    role_category = Column(String(100), nullable=True)

    # School year month 1..12 (Sept..Aug)
    month = Column(Integer, nullable=False, index=True)
    fte = Column(Float, nullable=False)

    created_at = Column(DateTime, server_default=func.now())

    monthly_run = relationship("MonthlyRun")
    municipality = relationship("Municipality")

    def __repr__(self):
        return (
            f"<StaffPosition scope={self.scope} "
            f"inst={self.institution_code or self.village_code} "
            f"role={self.role} m={self.month} fte={self.fte}>"
        )
