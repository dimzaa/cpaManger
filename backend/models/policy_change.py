"""
PolicyChange — a ministry policy change alert that affects one or more budget codes.
Municipalities can acknowledge they have read the change.
"""
import json
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Date, ForeignKey, func
from backend.database import Base


class PolicyChange(Base):
    __tablename__ = "policy_changes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    # formula | percentage | threshold | new_code | removed_code |
    # deadline | salary_table | eligibility
    change_type = Column(String(50), nullable=False, default="formula")
    affected_codes = Column(Text, nullable=True)           # JSON array of code strings ["3","19"]
    affected_municipalities = Column(Text, default="all")  # "all" or JSON array of IDs
    effective_date = Column(Date, nullable=True)
    announced_date = Column(Date, nullable=True)
    source = Column(String(500), nullable=True)            # circular number or announcement
    impact_description = Column(Text, nullable=True)
    action_required = Column(Text, nullable=True)
    action_deadline = Column(Date, nullable=True)
    # high | medium | low | info
    severity = Column(String(20), nullable=False, default="medium")
    is_acknowledged_by = Column(Text, default="[]")        # JSON array of municipality IDs
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # ── helpers ──────────────────────────────────────────────────────────
    def get_affected_codes(self) -> list:
        if not self.affected_codes:
            return []
        try:
            return json.loads(self.affected_codes)
        except Exception:
            return []

    def get_acknowledged_by(self) -> list:
        if not self.is_acknowledged_by:
            return []
        try:
            return json.loads(self.is_acknowledged_by)
        except Exception:
            return []

    def is_acknowledged_by_municipality(self, municipality_id: int) -> bool:
        return municipality_id in self.get_acknowledged_by()

    def add_acknowledgement(self, municipality_id: int):
        acked = self.get_acknowledged_by()
        if municipality_id not in acked:
            acked.append(municipality_id)
            self.is_acknowledged_by = json.dumps(acked)

    def __repr__(self):
        return f"<PolicyChange id={self.id} title={self.title[:40]} severity={self.severity}>"
