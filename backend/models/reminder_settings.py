"""
Reminder Settings — email/in-app toggle configuration per municipality (or global).
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from backend.database import Base


class ReminderSettings(Base):
    __tablename__ = "reminder_settings"

    id = Column(Integer, primary_key=True, index=True)
    # NULL = global settings for all municipalities
    municipality_id = Column(Integer, ForeignKey("municipalities.id", ondelete="CASCADE"), nullable=True, unique=True, index=True)
    email_enabled = Column(Boolean, default=True)
    in_app_enabled = Column(Boolean, default=True)
    whatsapp_enabled = Column(Boolean, default=False)
    contact_email = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ReminderSettings municipality_id={self.municipality_id}>"
