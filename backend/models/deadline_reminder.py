"""
Deadline Reminder — a single scheduled reminder for a municipality/deadline combination.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import relationship
from backend.database import Base


class DeadlineReminder(Base):
    __tablename__ = "deadline_reminders"

    id = Column(Integer, primary_key=True, index=True)
    deadline_id = Column(Integer, ForeignKey("reminder_deadlines.id", ondelete="CASCADE"), nullable=False, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id", ondelete="CASCADE"), nullable=False, index=True)
    reminder_date = Column(Date, nullable=False, index=True)
    days_before = Column(Integer, nullable=False)
    # pending | sent | failed | dismissed
    status = Column(String(20), nullable=False, default="pending", index=True)
    sent_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)
    dismissed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    deadline = relationship("MinistryDeadline", lazy="joined")
    municipality = relationship("Municipality", lazy="joined")

    def __repr__(self):
        return f"<DeadlineReminder id={self.id} muni={self.municipality_id} deadline={self.deadline_id} date={self.reminder_date} status={self.status}>"
