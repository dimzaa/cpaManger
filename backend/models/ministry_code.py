"""
MinistryCode — represents a single ministry budget code (e.g. code 3, 19, 33)
with metadata: formula, participation percent, booklet page, change triggers, etc.
"""
import json
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, DateTime, func
from backend.database import Base


class MinistryCode(Base):
    __tablename__ = "ministry_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name_short = Column(String(200), nullable=False)
    name_full = Column(String(500), nullable=False)
    # גני ילדים | חינוך יסודי | חטיבת ביניים | חטיבה עליונה |
    # חינוך מיוחד | נושאים רשותיים | הסעות | שירותים פסיכולוגיים
    category = Column(String(100), nullable=False, default="כללי")
    description = Column(Text, nullable=True)
    formula = Column(Text, nullable=True)
    participation_percent = Column(Float, nullable=True)
    constant_divisor = Column(Integer, nullable=True)
    # monthly | annual | quarterly | one_time
    payment_type = Column(String(50), nullable=False, default="monthly")
    # all | cities | regional_councils | recognized_unofficial
    applies_to = Column(String(50), nullable=False, default="all")
    booklet_page = Column(Integer, nullable=True)
    purple_book_column = Column(String(50), nullable=True)
    booklet_section = Column(String(300), nullable=True)
    is_deduction = Column(Boolean, default=False, nullable=False)
    # JSON arrays stored as text
    sub_topics = Column(Text, nullable=True)       # ["item1", ...]
    change_triggers = Column(Text, nullable=True)  # ["trigger1", ...]
    related_codes = Column(Text, nullable=True)    # ["19", "33", ...]
    keywords = Column(String(1000), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_updated = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # ── helpers ──────────────────────────────────────────────────────────
    def get_sub_topics(self) -> list:
        if not self.sub_topics:
            return []
        try:
            return json.loads(self.sub_topics)
        except Exception:
            return []

    def get_change_triggers(self) -> list:
        if not self.change_triggers:
            return []
        try:
            return json.loads(self.change_triggers)
        except Exception:
            return []

    def get_related_codes(self) -> list:
        if not self.related_codes:
            return []
        try:
            return json.loads(self.related_codes)
        except Exception:
            return []

    def __repr__(self):
        return f"<MinistryCode code={self.code} name={self.name_short}>"
