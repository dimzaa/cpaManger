"""
Ministry Deadline model — official Education Ministry submission deadlines.
"""
import json
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, func
from backend.database import Base


class MinistryDeadline(Base):
    __tablename__ = "reminder_deadlines"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    deadline_type = Column(String(20), nullable=False, default="annual")
    # For annual: month 1-12; for quarterly: stored as JSON list e.g. "[3,6,9,12]"
    deadline_month = Column(String(30), nullable=True)
    deadline_day = Column(Integer, nullable=False, default=31)
    # JSON array e.g. [60, 30, 14, 7, 1]
    reminder_days_before = Column(Text, nullable=False, default="[30, 14, 7, 1]")
    # JSON array of topic codes e.g. ["19"] or ["all"]
    topic_codes = Column(Text, nullable=False, default='["all"]')
    applies_to = Column(String(30), nullable=False, default="all")
    ministry_reference = Column(String(500), nullable=True)
    action_required = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def get_reminder_days(self):
        try:
            return json.loads(self.reminder_days_before)
        except Exception:
            return [30, 14, 7, 1]

    def get_topic_codes(self):
        try:
            return json.loads(self.topic_codes)
        except Exception:
            return ["all"]

    def get_deadline_months(self):
        """For quarterly deadlines returns list; for annual returns single-item list."""
        if not self.deadline_month:
            return []
        try:
            val = json.loads(self.deadline_month)
            if isinstance(val, list):
                return val
            return [int(val)]
        except Exception:
            try:
                return [int(self.deadline_month)]
            except Exception:
                return []

    def __repr__(self):
        return f"<MinistryDeadline id={self.id} title={self.title[:30]}>"
