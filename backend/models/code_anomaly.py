"""CodeAnomaly — Priority 4 long-form anomaly log."""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, UniqueConstraint, func
from sqlalchemy.orm import relationship
from backend.database import Base


class CodeAnomaly(Base):
    __tablename__ = "code_anomalies"
    __table_args__ = (
        UniqueConstraint("run_id", "topic_code", "flag_type", name="uq_anomaly_run_code_flag"),
    )

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("monthly_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=False, index=True)
    topic_code = Column(String(10), nullable=False, index=True)
    flag_type = Column(String(20), nullable=False, index=True)  # 'new'|'disappeared'|'outlier'|'tie_out_gap'

    previous_value = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)
    delta = Column(Float, nullable=True)
    delta_pct = Column(Float, nullable=True)
    narrative = Column(String(500), nullable=True)  # auto-generated Hebrew sentence

    acknowledged_by_cpa = Column(Boolean, default=False, nullable=False, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    run = relationship("MonthlyRun")
    municipality = relationship("Municipality")
