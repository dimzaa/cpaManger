"""
In-App Notification — stores notifications generated for municipalities/users.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, func
from backend.database import Base


class InAppNotification(Base):
    __tablename__ = "in_app_notifications"

    id = Column(Integer, primary_key=True, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    # deadline_reminder | budget_updated | suggestion_approved | suggestion_rejected | large_discrepancy | new_report
    type = Column(String(50), nullable=False, default="deadline_reminder")
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=True)
    action_url = Column(String(500), nullable=True)
    action_text = Column(String(200), nullable=True)
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    read_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<InAppNotification id={self.id} type={self.type} is_read={self.is_read}>"
