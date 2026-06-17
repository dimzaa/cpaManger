"""
MinistryCodeView — tracks when a user views a ministry code detail page.
Used for analytics: most-viewed codes, municipality engagement.
"""
from sqlalchemy import Column, Integer, ForeignKey, DateTime, func
from backend.database import Base


class MinistryCodeView(Base):
    __tablename__ = "ministry_code_views"

    id = Column(Integer, primary_key=True, index=True)
    code_id = Column(Integer, ForeignKey("ministry_codes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    viewed_at = Column(DateTime, server_default=func.now(), index=True)

    def __repr__(self):
        return f"<MinistryCodeView code_id={self.code_id} user_id={self.user_id}>"
