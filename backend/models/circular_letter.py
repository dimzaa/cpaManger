"""
CircularLetter — Ministry of Education circular (חוזר מנכ"ל).
Tracks which users have read each circular.
"""
import json
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Date, ForeignKey, func
from backend.database import Base


class CircularLetter(Base):
    __tablename__ = "circular_letters"

    id = Column(Integer, primary_key=True, index=True)
    circular_number = Column(String(100), nullable=True)   # e.g. "תשפ\"ו/3"
    title = Column(String(500), nullable=False)
    subject = Column(String(1000), nullable=True)          # brief summary
    full_content = Column(Text, nullable=True)
    published_date = Column(Date, nullable=True, index=True)
    effective_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    # תקצוב | כוח אדם | פדגוגיה | ביטחון | הסעות | כללי
    category = Column(String(50), nullable=False, default="כללי")
    affected_codes = Column(Text, nullable=True)           # JSON array of code strings
    affected_municipality_types = Column(Text, default="all")  # "all" or JSON
    # critical | important | routine
    importance = Column(String(20), nullable=False, default="routine")
    action_required = Column(Text, nullable=True)
    action_deadline = Column(Date, nullable=True)
    attachment_url = Column(String(500), nullable=True)
    tags = Column(Text, nullable=True)                     # JSON array of Hebrew tags
    read_by = Column(Text, default="[]")                   # JSON array of user IDs
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

    def get_tags(self) -> list:
        if not self.tags:
            return []
        try:
            return json.loads(self.tags)
        except Exception:
            return []

    def get_read_by(self) -> list:
        if not self.read_by:
            return []
        try:
            return json.loads(self.read_by)
        except Exception:
            return []

    def is_read_by_user(self, user_id: int) -> bool:
        return user_id in self.get_read_by()

    def mark_read(self, user_id: int):
        readers = self.get_read_by()
        if user_id not in readers:
            readers.append(user_id)
            self.read_by = json.dumps(readers)

    def __repr__(self):
        return f"<CircularLetter id={self.id} number={self.circular_number} importance={self.importance}>"
