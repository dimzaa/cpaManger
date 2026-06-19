"""
TopicSummary — Priority 2 denormalised cache.

One row per (run_id, topic_code). Populated at upload time by
backend.services.topic_summary_service.recompute_topic_summaries_for_run.

Powers the dashboard's per-topic table without scanning budget_lines
on every page load. Sourced from:
  * budget_lines  → amount_total / regular / retro_pos / retro_neg / institutions
  * monthly_runs  → prev_run_id (prior month for this muni)
  * ingestion_warnings → tie_out_diff
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, func
)
from sqlalchemy.orm import relationship

from backend.database import Base


class TopicSummary(Base):
    __tablename__ = "topic_summaries"
    __table_args__ = (
        UniqueConstraint("run_id", "topic_code", name="uq_topic_summary_run_code"),
    )

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("monthly_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=False, index=True)
    topic_code = Column(String(10), nullable=False, index=True)
    topic_name = Column(String(255), nullable=True)

    # Aggregates from budget_lines
    amount_total = Column(Float, nullable=False, default=0.0)
    amount_regular = Column(Float, nullable=False, default=0.0)
    amount_retro_pos = Column(Float, nullable=False, default=0.0)
    amount_retro_neg = Column(Float, nullable=False, default=0.0)

    # Month-over-month
    prev_run_id = Column(Integer, ForeignKey("monthly_runs.id"), nullable=True, index=True)
    prev_month_amount = Column(Float, nullable=True)
    delta_abs = Column(Float, nullable=True)
    delta_pct = Column(Float, nullable=True)

    # Flags
    anomaly_flag = Column(String(20), nullable=False, default="normal")  # new | outlier | normal
    tie_out_diff = Column(Float, nullable=False, default=0.0)

    # Institution drilldown
    n_institutions = Column(Integer, nullable=False, default=0)
    top_institution_code = Column(String(20), nullable=True)
    top_institution_name = Column(String(255), nullable=True)
    top_institution_amount = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    run = relationship("MonthlyRun", foreign_keys=[run_id])
    municipality = relationship("Municipality")

    def __repr__(self):
        return f"<TopicSummary run={self.run_id} code={self.topic_code} total={self.amount_total} flag={self.anomaly_flag}>"
