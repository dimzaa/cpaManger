"""
CodeHistory — Priority 3 denormalised time-series.

One row per (municipality_id, topic_code, year_month). Powers the
muni-portal sparklines, YTD calculations, and "show me code X over the
last 12 months" queries without scanning budget_lines.

Indexed by (muni, code) — the lookup pattern is "fetch history for one
topic in one muni". topic_summaries (Priority 2) is indexed by (run, code)
— the lookup pattern there is "fetch all topics for this run".
Complementary, both populated at upload time.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, func
)
from sqlalchemy.orm import relationship

from backend.database import Base


class CodeHistory(Base):
    __tablename__ = "code_history"
    __table_args__ = (
        UniqueConstraint(
            "municipality_id", "topic_code", "year_month",
            name="uq_code_history_muni_code_month",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=False, index=True)
    topic_code = Column(String(10), nullable=False, index=True)
    year_month = Column(String(7), nullable=False, index=True)  # YYYY-MM
    run_id = Column(Integer, ForeignKey("monthly_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    topic_name = Column(String(255), nullable=True)
    amount_total = Column(Float, nullable=False, default=0.0)
    amount_regular = Column(Float, nullable=False, default=0.0)
    amount_retro_pos = Column(Float, nullable=False, default=0.0)
    amount_retro_neg = Column(Float, nullable=False, default=0.0)
    line_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, server_default=func.now())

    municipality = relationship("Municipality")
    run = relationship("MonthlyRun")

    def __repr__(self):
        return f"<CodeHistory muni={self.municipality_id} code={self.topic_code} ym={self.year_month} total={self.amount_total}>"
