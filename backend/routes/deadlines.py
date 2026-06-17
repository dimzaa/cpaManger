"""
׳™׳•׳׳ ׳׳•׳¢׳“׳™׳ ׳•׳׳¢׳§׳‘ ׳‘׳§׳©׳•׳× ג€” Deadlines & Application Tracking

Tables:
  ministry_deadlines      ג€” Ministry submission deadlines (annual)
  application_tracking    ג€” Municipality tracking of each deadline per year
  position_gaps_history   ג€” Auto-saved monthly gap snapshots

Endpoints:
  GET  /api/deadlines/{municipality_id}
  POST /api/deadlines/{municipality_id}/{deadline_id}/application
  GET  /api/positions/gaps-history/{municipality_id}/{position_type}
  GET  /api/positions/priority/{municipality_id}/{month}
"""

import json
import logging
import math
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, Date, DateTime, func, text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db, engine, Base
from backend.models.municipality import Municipality
from backend.models.user import User
from backend.utils.auth_guards import require_login

logger = logging.getLogger(__name__)

router = APIRouter(tags=["deadlines"])

# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
# SQLAlchemy models (defined inline, created at startup)
# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

class AppDeadline(Base):
    __tablename__ = "ministry_deadlines"
    __table_args__ = {"extend_existing": True}

    id               = Column(Integer, primary_key=True, autoincrement=True)
    code             = Column(String, unique=True, nullable=False)
    title_hebrew     = Column(String, nullable=False)
    description      = Column(Text, default="")
    position_type    = Column(String, default="general")
    deadline_month   = Column(Integer, nullable=False)
    deadline_day     = Column(Integer, nullable=False)
    is_annual        = Column(Boolean, default=True)
    consequence      = Column(Text, default="")
    how_to_submit    = Column(Text, default="")
    ministry_form_name = Column(String, default="")
    ministry_system  = Column(String, default="portal")  # portal|amchi|email|phone
    requires_documents = Column(Text, default="[]")      # JSON array
    created_at       = Column(DateTime, default=datetime.utcnow)


class ApplicationTracking(Base):
    __tablename__ = "application_tracking"
    __table_args__ = {"extend_existing": True}

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    municipality_id     = Column(Integer, nullable=False, index=True)
    deadline_id         = Column(Integer, nullable=False)
    academic_year       = Column(String, nullable=False)   # "2025-2026"
    status              = Column(String, default="not_started")
    submitted_date      = Column(String, nullable=True)    # YYYY-MM-DD string
    submitted_by        = Column(Integer, nullable=True)   # user_id
    reference_number    = Column(String, nullable=True)
    notes               = Column(Text, default="")
    documents_attached  = Column(Text, default="[]")       # JSON array
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PositionGapsHistory(Base):
    __tablename__ = "position_gaps_history"
    __table_args__ = {"extend_existing": True}

    id               = Column(Integer, primary_key=True, autoincrement=True)
    municipality_id  = Column(Integer, nullable=False, index=True)
    month            = Column(String, nullable=False)          # YYYY-MM
    position_type    = Column(String, nullable=False)
    current_value    = Column(Float, default=0)
    entitled_value   = Column(Float, default=0)
    gap_value        = Column(Float, default=0)
    gap_amount       = Column(Float, default=0)
    created_at       = Column(DateTime, default=datetime.utcnow)


def _create_deadlines_tables():
    """Create the 3 new tables if they don't exist."""
    Base.metadata.create_all(bind=engine, tables=[
        AppDeadline.__table__,
        ApplicationTracking.__table__,
        PositionGapsHistory.__table__,
    ])


# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
# Seed data
# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
SEED_DEADLINES = [
    {
        "code": "ASSISTANTS_JULY",
        "title_hebrew": "׳”׳’׳©׳× ׳‘׳§׳©׳× ׳¢׳•׳–׳¨׳•׳× ׳’׳ ׳ ׳•׳×",
        "description": "׳‘׳§׳©׳” ׳׳׳™׳©׳•׳¨ ׳×׳§׳ ׳¢׳•׳–׳¨׳•׳× ׳’׳ ׳ ׳•׳× ׳׳©׳ ׳× ׳׳™׳׳•׳“׳™׳ ׳”׳‘׳׳”",
        "position_type": "assistants",
        "deadline_month": 7,
        "deadline_day": 31,
        "is_annual": True,
        "consequence": "׳׳׳ ׳”׳’׳©׳” ׳¢׳“ ׳”׳׳•׳¢׳“ ג€” ׳”׳‘׳§׳©׳” ׳×׳™׳“׳—׳” ׳¢׳ ׳”׳¡׳£",
        "how_to_submit": "1. ׳›׳ ׳¡ ׳׳₪׳•׳¨׳˜׳ ׳¨׳©׳•׳™׳•׳× ׳•׳‘׳¢׳׳•׳™׳•׳×\n2. ׳׳—׳¥ ׳¢׳ '׳×׳׳׳™׳“׳™׳' ג†’ '׳’׳ ׳™ ׳™׳׳“׳™׳'\n3. ׳׳׳ ׳˜׳•׳₪׳¡ ׳‘׳§׳©׳× ׳×׳§׳ ׳¢׳•׳–׳¨׳•׳×\n4. ׳¦׳¨׳£ ׳¨׳©׳™׳׳× ׳™׳׳“׳™׳ ׳׳¢׳•׳“׳›׳ ׳×\n5. ׳©׳׳— ׳׳׳’׳£ ׳‘׳›׳™׳¨ ׳׳׳—'׳™",
        "ministry_system": "portal",
        "requires_documents": json.dumps(["׳¨׳©׳™׳׳× ׳™׳׳“׳™׳ ׳׳¢׳•׳“׳›׳ ׳×", "׳׳™׳©׳•׳¨ ׳‘׳˜׳™׳—׳•׳× ׳’׳", "׳׳™׳©׳•׳¨ ׳׳ ׳”׳ ׳—׳™׳ ׳•׳ ׳”׳¨׳©׳•׳×"]),
    },
    {
        "code": "COMPLETION_DECEMBER",
        "title_hebrew": "׳‘׳§׳©׳× ׳™׳׳“׳™ ׳”׳©׳׳׳”",
        "description": "׳‘׳§׳©׳” ׳׳׳™׳©׳•׳¨ ׳™׳׳“׳™ ׳”׳©׳׳׳” ׳׳’׳ ׳™׳ ׳¢׳ ׳₪׳—׳•׳× ׳-28 ׳™׳׳“׳™׳",
        "position_type": "completion",
        "deadline_month": 12,
        "deadline_day": 31,
        "is_annual": True,
        "consequence": "׳‘׳§׳©׳•׳× ׳©׳™׳’׳™׳¢׳• ׳׳—׳¨׳™ 31.12 ׳™׳™׳“׳—׳• ׳¢׳ ׳”׳¡׳£ ׳׳׳ ׳“׳™׳•׳",
        "how_to_submit": "1. ׳›׳ ׳¡ ׳׳׳¢׳¨׳›׳× ׳’׳ ׳™ ׳™׳׳“׳™׳-׳™׳׳“׳™ ׳”׳©׳׳׳”\n2. ׳§׳™׳©׳•׳¨: apps.education.gov.il/gylnetnew\n3. ׳׳׳ ׳˜׳•׳₪׳¡ ׳‘׳§׳©׳” ׳¢׳‘׳•׳¨ ׳›׳ ׳’׳ ׳–׳›׳׳™\n4. ׳¦׳™׳™׳ ׳׳¡׳₪׳¨ ׳™׳׳“׳™׳ ׳‘׳₪׳•׳¢׳ ׳•׳׳¡׳₪׳¨ ׳™׳׳“׳™ ׳”׳©׳׳׳” ׳”׳׳‘׳•׳§׳©",
        "ministry_system": "portal",
        "requires_documents": json.dumps(["׳¨׳©׳™׳׳× ׳™׳׳“׳™׳ ׳‘׳’׳", "׳”׳•׳›׳—׳× ׳׳¡׳₪׳¨ ׳™׳׳“׳™׳ (׳₪׳—׳•׳× ׳-28)"]),
    },
    {
        "code": "NEW_KINDERGARTEN_APRIL",
        "title_hebrew": "׳‘׳§׳©׳× ׳₪׳×׳™׳—׳× ׳’׳ ׳™׳׳“׳™׳ ׳—׳“׳©",
        "description": "׳‘׳§׳©׳” ׳׳₪׳×׳™׳—׳× ׳›׳™׳×׳× ׳’׳ ׳ ׳•׳¡׳₪׳× ׳׳©׳ ׳× ׳”׳׳™׳׳•׳“׳™׳ ׳”׳‘׳׳”",
        "position_type": "kindergartens",
        "deadline_month": 4,
        "deadline_day": 30,
        "is_annual": True,
        "consequence": "׳₪׳×׳™׳—׳× ׳’׳ ׳™׳ ׳׳׳ ׳׳™׳©׳•׳¨ ג€” ׳¢׳׳•׳× ׳”׳’׳ ׳ ׳× ׳×׳§׳•׳–׳– ׳׳”׳¨׳©׳•׳×",
        "how_to_submit": "1. ׳”׳’׳© ׳‘׳§׳©׳” ׳׳׳’׳£ ׳‘׳›׳™׳¨ ׳׳׳—'׳™\n2. ׳¦׳¨׳£ ׳ ׳×׳•׳ ׳™ ׳¨׳™׳©׳•׳\n3. ׳”׳׳×׳ ׳׳׳™׳©׳•׳¨ ׳”׳׳—׳•׳–\n4. ׳§׳׳™׳˜׳× ׳”׳™׳׳“ ׳”׳§׳•׳‘׳¢ (׳™׳׳“ ׳׳¡׳₪׳¨ 36)",
        "ministry_system": "amchi",
        "requires_documents": json.dumps(["׳˜׳•׳₪׳¡ ׳‘׳§׳©׳× ׳×׳§׳ ׳’׳", "׳ ׳×׳•׳ ׳™ ׳¨׳™׳©׳•׳ ׳¢׳“׳›׳ ׳™׳™׳", "׳׳™׳©׳•׳¨ ׳©׳˜׳— ׳”׳’׳ (׳×׳¡׳¨׳™׳˜)"]),
    },
    {
        "code": "REGISTRATION_MARCH",
        "title_hebrew": "׳”׳’׳©׳× ׳ ׳×׳•׳ ׳™ ׳¨׳™׳©׳•׳ ׳’׳ ׳™ ׳™׳׳“׳™׳",
        "description": "׳“׳™׳•׳•׳— ׳׳¡׳₪׳¨ ׳™׳׳“׳™׳ ׳”׳¨׳©׳•׳׳™׳ ׳׳›׳ ׳׳’׳׳” ׳׳©׳ ׳” ׳”׳‘׳׳”",
        "position_type": "general",
        "deadline_month": 3,
        "deadline_day": 30,
        "is_annual": True,
        "consequence": "׳׳™׳—׳•׳¨ ׳‘׳“׳™׳•׳•׳— ג€” ׳×׳©׳׳•׳׳™ ׳¡׳₪׳˜׳׳‘׳¨ ׳׳ ׳™׳›׳׳׳• ׳׳× ׳›׳ ׳”׳™׳׳“׳™׳",
        "how_to_submit": "1. ׳›׳ ׳¡ ׳׳׳¢׳¨׳›׳× ׳¡׳™׳“׳•׳¨ ׳’׳ ׳™׳\n2. ׳׳׳ ׳ ׳×׳•׳ ׳™ ׳¨׳™׳©׳•׳ ׳׳₪׳™ ׳׳’׳׳”\n3. ׳׳©׳¨ ׳•׳©׳׳— ׳׳׳—׳•׳–",
        "ministry_system": "portal",
        "requires_documents": json.dumps(["׳¨׳©׳™׳׳× ׳¨׳™׳©׳•׳ ׳׳׳׳”"]),
    },
    {
        "code": "SIX_DAY_REPORT",
        "title_hebrew": "׳“׳™׳•׳•׳— ׳’׳ ׳™׳ ׳”׳₪׳•׳¢׳׳™׳ 6 ׳™׳׳™׳",
        "description": "׳“׳™׳•׳•׳— ׳¢׳ ׳’׳ ׳™׳ ׳”׳׳₪׳¢׳™׳׳™׳ ׳™׳•׳ ׳׳™׳׳•׳“׳™׳ ׳ ׳•׳¡׳£ (׳™׳•׳ ׳•')",
        "position_type": "six_day",
        "deadline_month": 9,
        "deadline_day": 1,
        "is_annual": True,
        "consequence": "׳׳׳ ׳“׳™׳•׳•׳— ג€” ׳׳ ׳×׳§׳‘׳ ׳×׳•׳¡׳₪׳× 17.85% ׳¢׳ ׳¢׳׳•׳× ׳”׳¢׳•׳–׳¨׳×",
        "how_to_submit": "1. ׳₪׳ ׳” ׳׳׳—׳•׳– ׳‘׳›׳×׳‘\n2. ׳¦׳™׳™׳ ׳׳™׳׳• ׳’׳ ׳™׳ ׳₪׳•׳¢׳׳™׳ 6 ׳™׳׳™׳\n3. ׳¦׳¨׳£ ׳׳™׳©׳•׳¨ ׳”׳ ׳”׳׳× ׳”׳’׳",
        "ministry_system": "email",
        "requires_documents": json.dumps(["׳׳™׳©׳•׳¨ ׳”׳ ׳”׳׳× ׳’׳ ׳¢׳ ׳₪׳¢׳™׳׳•׳× 6 ׳™׳׳™׳"]),
    },
    {
        "code": "OFFICER_ANNUAL",
        "title_hebrew": "׳‘׳“׳™׳§׳× ׳–׳›׳׳•׳× ׳§׳¦׳™׳ ׳‘׳™׳§׳•׳¨ ׳¡׳“׳™׳¨",
        "description": "׳‘׳“׳™׳§׳” ׳©׳ ׳×׳™׳× ׳©׳ ׳–׳›׳׳•׳× ׳•׳×׳§׳ ׳§׳¦׳™׳ ׳‘׳™׳§׳•׳¨ ׳¡׳“׳™׳¨",
        "position_type": "officer",
        "deadline_month": 8,
        "deadline_day": 31,
        "is_annual": True,
        "consequence": "׳׳™ ׳‘׳“׳™׳§׳” ג€” ׳™׳™׳×׳›׳ ׳׳•׳‘׳“׳ ׳×׳§׳ ׳׳׳•׳©׳¨",
        "how_to_submit": "1. ׳₪׳ ׳” ׳׳׳₪׳§׳— ׳‘׳™׳§׳•׳¨ ׳¡׳“׳™׳¨ ׳‘׳׳—׳•׳–\n2. ׳”׳’׳© ׳“׳•׳— ׳₪׳¢׳™׳׳•׳× ׳©׳ ׳×׳™\n3. ׳‘׳§׳© ׳¢׳“׳›׳•׳ ׳×׳§׳ ׳‘׳׳™׳“׳× ׳”׳¦׳•׳¨׳",
        "ministry_system": "phone",
        "requires_documents": json.dumps(["׳“׳•׳— ׳₪׳¢׳™׳׳•׳× ׳§׳¦׳™׳ ׳‘׳™׳§׳•׳¨ ׳¡׳“׳™׳¨"]),
    },
]


def seed_ministry_deadlines(db: Session):
    """Insert seed deadline records if they don't exist yet."""
    for item in SEED_DEADLINES:
        existing = db.query(AppDeadline).filter(AppDeadline.code == item["code"]).first()
        if not existing:
            db.add(AppDeadline(**item))
    db.commit()


# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
# Helpers
# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

def _get_academic_year(ref_date: date = None) -> str:
    """
    If month >= September ג†’ "YYYY-YYYY+1"
    If month < September  ג†’ "YYYY-1-YYYY"
    """
    d = ref_date or date.today()
    if d.month >= 9:
        return f"{d.year}-{d.year + 1}"
    else:
        return f"{d.year - 1}-{d.year}"


def _get_deadline_date(deadline: AppDeadline, today: date) -> date:
    """
    Return the NEXT occurrence of this deadline (same year or next year if passed).
    """
    try:
        d = date(today.year, deadline.deadline_month, deadline.deadline_day)
    except ValueError:
        # e.g. Feb 30 ג†’ clamp to last day
        import calendar
        last_day = calendar.monthrange(today.year, deadline.deadline_month)[1]
        d = date(today.year, deadline.deadline_month, min(deadline.deadline_day, last_day))
    # If already passed this year, use next year's date
    if d < today and deadline.is_annual:
        try:
            d = date(today.year + 1, deadline.deadline_month, deadline.deadline_day)
        except ValueError:
            import calendar
            last_day = calendar.monthrange(today.year + 1, deadline.deadline_month)[1]
            d = date(today.year + 1, deadline.deadline_month, min(deadline.deadline_day, last_day))
    return d


def _deadline_display(d: date) -> str:
    HEB_MONTHS = {
        1: "׳™׳ ׳•׳׳¨", 2: "׳₪׳‘׳¨׳•׳׳¨", 3: "׳׳¨׳¥", 4: "׳׳₪׳¨׳™׳", 5: "׳׳׳™", 6: "׳™׳•׳ ׳™",
        7: "׳™׳•׳׳™", 8: "׳׳•׳’׳•׳¡׳˜", 9: "׳¡׳₪׳˜׳׳‘׳¨", 10: "׳׳•׳§׳˜׳•׳‘׳¨", 11: "׳ ׳•׳‘׳׳‘׳¨", 12: "׳“׳¦׳׳‘׳¨",
    }
    return f"{d.day} ׳‘{HEB_MONTHS[d.month]} {d.year}"


def _urgency(days_until: int) -> str:
    if days_until < 0:
        return "overdue"
    if days_until <= 14:
        return "critical"
    if days_until <= 30:
        return "urgent"
    if days_until <= 60:
        return "attention"
    if days_until <= 90:
        return "upcoming"
    return "future"


def _status_from_days(days_until: int) -> str:
    if days_until < 0:
        return "overdue"
    if days_until <= 14:
        return "critical"
    if days_until <= 60:
        return "upcoming"
    return "future"


SYSTEM_LABELS = {
    "portal": "׳₪׳•׳¨׳˜׳ ׳¨׳©׳•׳™׳•׳× ׳•׳‘׳¢׳׳•׳™׳•׳×",
    "amchi": "׳׳’׳£ ׳‘׳›׳™׳¨ ׳׳׳—'׳™",
    "email": "׳׳™׳׳™׳™׳ ׳׳׳—׳•׳–",
    "phone": "׳˜׳׳₪׳•׳ ׳׳׳₪׳§׳—",
}

POSITION_TYPE_DISPLAY = {
    "assistants": "׳¢׳•׳–׳¨׳•׳× ׳’׳ ׳ ׳•׳×",
    "kindergartens": "׳’׳ ׳™׳׳“׳™׳ ׳ ׳•׳¡׳£",
    "completion": "׳™׳׳“׳™ ׳”׳©׳׳׳”",
    "six_day": "׳’׳ 6 ׳™׳׳™׳",
    "officer": "׳§׳¦׳™׳ ׳‘׳™׳§׳•׳¨ ׳¡׳“׳™׳¨",
    "general": "׳›׳׳׳™",
}

# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
# Pydantic schemas
# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

class ApplicationIn(BaseModel):
    status: str
    submitted_date: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class ApplicationOut(BaseModel):
    id: int
    deadline_id: int
    municipality_id: int
    academic_year: str
    status: str
    submitted_date: Optional[str]
    reference_number: Optional[str]
    notes: Optional[str]
    updated_at: str


# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
# ENDPOINT 1 ג€” Get All Deadlines with Status
# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

@router.get("/api/deadlines/{municipality_id}")
async def get_deadlines(
    municipality_id: int,
    year: Optional[str] = None,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Return all ministry deadlines enriched with this municipality's application status."""
    if current_user.role == "municipality" and current_user.municipality_id != municipality_id:
        raise HTTPException(status_code=403, detail="׳׳™׳ ׳”׳¨׳©׳׳” ׳׳¦׳₪׳•׳× ׳‘׳ ׳×׳•׳ ׳™ ׳¨׳©׳•׳× ׳׳—׳¨׳×")

    today = date.today()
    academic_year = year or _get_academic_year(today)

    deadlines = db.query(AppDeadline).order_by(
        AppDeadline.deadline_month, AppDeadline.deadline_day
    ).all()

    # Cache all application_tracking rows for this municipality+year
    apps = db.query(ApplicationTracking).filter(
        ApplicationTracking.municipality_id == municipality_id,
        ApplicationTracking.academic_year == academic_year,
    ).all()
    app_by_deadline: Dict[int, ApplicationTracking] = {a.deadline_id: a for a in apps}

    result = []
    upcoming_count = 0
    overdue_count = 0

    for dl in deadlines:
        dl_date = _get_deadline_date(dl, today)
        days_until = (dl_date - today).days
        urgency = _urgency(days_until)

        if days_until < 0:
            overdue_count += 1
        elif days_until <= 90:
            upcoming_count += 1

        app = app_by_deadline.get(dl.id)
        app_data = None
        if app:
            app_data = {
                "id": app.id,
                "status": app.status,
                "submitted_date": app.submitted_date,
                "reference_number": app.reference_number,
                "notes": app.notes,
                "updated_at": app.updated_at.isoformat() if app.updated_at else None,
            }

        try:
            docs = json.loads(dl.requires_documents or "[]")
        except Exception:
            docs = []

        result.append({
            "id": dl.id,
            "code": dl.code,
            "title": dl.title_hebrew,
            "description": dl.description,
            "position_type": dl.position_type,
            "position_type_display": POSITION_TYPE_DISPLAY.get(dl.position_type, dl.position_type),
            "deadline_date": dl_date.isoformat(),
            "deadline_display": _deadline_display(dl_date),
            "deadline_month": dl.deadline_month,
            "deadline_day": dl.deadline_day,
            "days_until": days_until,
            "status": _status_from_days(days_until),
            "urgency": urgency,
            "consequence": dl.consequence,
            "how_to_submit": dl.how_to_submit,
            "ministry_system": dl.ministry_system,
            "ministry_system_display": SYSTEM_LABELS.get(dl.ministry_system, dl.ministry_system),
            "requires_documents": docs,
            "application": app_data,
        })

    # Sort by deadline date
    result.sort(key=lambda x: x["deadline_date"])

    return {
        "academic_year": academic_year,
        "current_date": today.isoformat(),
        "upcoming_count": upcoming_count,
        "overdue_count": overdue_count,
        "deadlines": result,
    }


# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
# ENDPOINT 2 ג€” Update Application Status
# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

@router.post("/api/deadlines/{municipality_id}/{deadline_id}/application")
async def update_application(
    municipality_id: int,
    deadline_id: int,
    body: ApplicationIn,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Create or update the application tracking record for a deadline."""
    if current_user.role == "municipality" and current_user.municipality_id != municipality_id:
        raise HTTPException(status_code=403, detail="׳׳™׳ ׳”׳¨׳©׳׳” ׳׳¢׳“׳›׳ ׳ ׳×׳•׳ ׳™ ׳¨׳©׳•׳× ׳׳—׳¨׳×")

    academic_year = _get_academic_year()

    # Check deadline exists
    dl = db.query(AppDeadline).filter(AppDeadline.id == deadline_id).first()
    if not dl:
        raise HTTPException(status_code=404, detail="׳”׳׳•׳¢׳“ ׳׳ ׳ ׳׳¦׳")

    # Validate status
    VALID_STATUSES = {"not_started", "in_progress", "submitted", "approved", "rejected", "not_relevant"}
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"׳¡׳˜׳˜׳•׳¡ ׳׳ ׳×׳§׳™׳: {body.status}")

    # Find or create application
    app = db.query(ApplicationTracking).filter(
        ApplicationTracking.municipality_id == municipality_id,
        ApplicationTracking.deadline_id == deadline_id,
        ApplicationTracking.academic_year == academic_year,
    ).first()

    now = datetime.utcnow()

    if app:
        app.status = body.status
        app.submitted_date = body.submitted_date
        app.reference_number = body.reference_number
        app.notes = body.notes or ""
        app.updated_at = now
        if body.status == "submitted" and not app.submitted_by:
            app.submitted_by = current_user.id
    else:
        app = ApplicationTracking(
            municipality_id=municipality_id,
            deadline_id=deadline_id,
            academic_year=academic_year,
            status=body.status,
            submitted_date=body.submitted_date,
            submitted_by=current_user.id if body.status == "submitted" else None,
            reference_number=body.reference_number,
            notes=body.notes or "",
            created_at=now,
            updated_at=now,
        )
        db.add(app)

    db.commit()
    db.refresh(app)

    return {
        "id": app.id,
        "deadline_id": app.deadline_id,
        "municipality_id": app.municipality_id,
        "academic_year": app.academic_year,
        "status": app.status,
        "submitted_date": app.submitted_date,
        "reference_number": app.reference_number,
        "notes": app.notes,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
    }


# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
# ENDPOINT 3 ג€” Historical Gap Data
# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

HEB_MONTHS_MAP = {
    "01": "׳™׳ ׳•׳׳¨", "02": "׳₪׳‘׳¨׳•׳׳¨", "03": "׳׳¨׳¥", "04": "׳׳₪׳¨׳™׳",
    "05": "׳׳׳™", "06": "׳™׳•׳ ׳™", "07": "׳™׳•׳׳™", "08": "׳׳•׳’׳•׳¡׳˜",
    "09": "׳¡׳₪׳˜׳׳‘׳¨", "10": "׳׳•׳§׳˜׳•׳‘׳¨", "11": "׳ ׳•׳‘׳׳‘׳¨", "12": "׳“׳¦׳׳‘׳¨",
}

POSITION_DISPLAY_NAMES = {
    "assistants": "׳¢׳•׳–׳¨׳•׳× ׳’׳ ׳ ׳•׳×",
    "kindergartens": "׳’׳ ׳™׳׳“׳™׳ ׳ ׳•׳¡׳£",
    "completion_children": "׳™׳׳“׳™ ׳”׳©׳׳׳”",
    "six_day": "׳’׳ 6 ׳™׳׳™׳",
    "attendance_officer": "׳§׳¦׳™׳ ׳‘׳™׳§׳•׳¨ ׳¡׳“׳™׳¨",
}


def _month_display(month_str: str) -> str:
    if not month_str or len(month_str) < 7:
        return month_str
    y, m = month_str[:4], month_str[5:7]
    return f"{HEB_MONTHS_MAP.get(m, m)} {y}"


@router.get("/api/positions/gaps-history/{municipality_id}/{position_type}")
async def get_gap_history(
    municipality_id: int,
    position_type: str,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Return last 6 months of gap data for a specific position type."""
    if current_user.role == "municipality" and current_user.municipality_id != municipality_id:
        raise HTTPException(status_code=403, detail="׳׳™׳ ׳”׳¨׳©׳׳”")

    rows = (
        db.query(PositionGapsHistory)
        .filter(
            PositionGapsHistory.municipality_id == municipality_id,
            PositionGapsHistory.position_type == position_type,
        )
        .order_by(PositionGapsHistory.month)
        .all()
    )

    # Last 6 entries
    rows = rows[-6:]

    history = []
    total_lost = 0.0
    consecutive = 0

    for r in rows:
        history.append({
            "month": r.month,
            "month_display": _month_display(r.month),
            "current": r.current_value,
            "entitled": r.entitled_value,
            "gap": r.gap_value,
            "gap_amount": r.gap_amount,
            "had_gap": r.gap_value > 0,
        })
        if r.gap_value > 0:
            total_lost += r.gap_amount

    # Count trailing consecutive months with gap
    consecutive = 0
    for r in reversed(rows):
        if r.gap_value > 0:
            consecutive += 1
        else:
            break

    position_name = POSITION_DISPLAY_NAMES.get(position_type, position_type)

    message = ""
    if consecutive >= 2:
        message = f"׳—׳•׳¡׳¨ ׳–׳” ׳§׳™׳™׳ ׳›׳‘׳¨ {consecutive} ׳—׳•׳“׳©׳™׳ ׳¨׳¦׳•׳₪׳™׳ ג€” ג‚×{total_lost:,.0f} ׳”׳₪׳¡׳“ ׳׳¦׳˜׳‘׳¨"
    elif consecutive == 1:
        message = "׳—׳•׳¡׳¨ ׳—׳“׳© ג€” ׳–׳•׳”׳” ׳—׳•׳“׳© ׳׳—׳“"

    return {
        "position_type": position_type,
        "position_name": position_name,
        "history": history,
        "consecutive_months_with_gap": consecutive,
        "total_lost_value": round(total_lost),
        "message": message,
    }


# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
# ENDPOINT 4 ג€” Priority Score
# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

# Map position id ג†’ deadline code
POSITION_DEADLINE_MAP = {
    "assistants":          "ASSISTANTS_JULY",
    "completion_children": "COMPLETION_DECEMBER",
    "kindergartens":       "NEW_KINDERGARTEN_APRIL",
    "six_day":             "SIX_DAY_REPORT",
    "attendance_officer":  "OFFICER_ANNUAL",
}

PRIORITY_LABELS = [
    (400_000, "ג¡ ׳¢׳“׳™׳₪׳•׳× ׳’׳‘׳•׳”׳” ׳׳׳•׳“", "red"),
    (150_000, "ג ן¸ ׳¢׳“׳™׳₪׳•׳× ׳’׳‘׳•׳”׳”", "amber"),
    (50_000,  "נ“‹ ׳¢׳“׳™׳₪׳•׳× ׳‘׳™׳ ׳•׳ ׳™׳×", "blue"),
    (0,       "נ“ ׳¢׳“׳™׳₪׳•׳× ׳ ׳׳•׳›׳”", "gray"),
]


def _priority_label(score: float):
    for threshold, label, color in PRIORITY_LABELS:
        if score >= threshold:
            return label, color
    return "נ“ ׳¢׳“׳™׳₪׳•׳× ׳ ׳׳•׳›׳”", "gray"


@router.get("/api/positions/priority/{municipality_id}/{month}")
async def get_priority_score(
    municipality_id: int,
    month: str,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Calculate and return priority scores for all position gaps."""
    if current_user.role == "municipality" and current_user.municipality_id != municipality_id:
        raise HTTPException(status_code=403, detail="׳׳™׳ ׳”׳¨׳©׳׳”")

    # Get positions analysis (lazy import to avoid circular imports)
    from backend.routes.positions import calculate_positions_for_municipality

    municipality = db.query(Municipality).filter(Municipality.id == municipality_id).first()
    if not municipality:
        raise HTTPException(status_code=404, detail="׳”׳¨׳©׳•׳× ׳”׳׳§׳•׳׳™׳× ׳׳ ׳ ׳׳¦׳׳”")

    analysis = calculate_positions_for_municipality(municipality, month, db)
    today = date.today()

    # Load deadlines
    deadlines = db.query(AppDeadline).all()
    dl_by_code: Dict[str, AppDeadline] = {d.code: d for d in deadlines}

    # Load gap history for each position type
    history_rows = db.query(PositionGapsHistory).filter(
        PositionGapsHistory.municipality_id == municipality_id,
    ).all()
    history_by_type: Dict[str, List] = {}
    for r in history_rows:
        history_by_type.setdefault(r.position_type, []).append(r)

    priorities = []
    total_annual = 0.0
    total_lost_all = 0.0

    for pos in analysis.positions:
        if pos.gap_direction != "missing" or pos.gap <= 0:
            continue

        annual_value = pos.annual_gap_value
        if annual_value <= 0:
            continue
        total_annual += annual_value

        # Gap history for this position
        hist = sorted(history_by_type.get(pos.id, []), key=lambda r: r.month)
        consecutive = 0
        lost_so_far = 0.0
        for r in reversed(hist):
            if r.gap_value > 0:
                consecutive += 1
                lost_so_far += r.gap_amount
            else:
                break

        # Consecutive months factor
        if consecutive >= 4:
            consec_factor = 2.0
        elif consecutive == 3:
            consec_factor = 1.6
        elif consecutive == 2:
            consec_factor = 1.3
        else:
            consec_factor = 1.0

        # Urgency multiplier (based on nearest deadline)
        dl_code = POSITION_DEADLINE_MAP.get(pos.id)
        dl = dl_by_code.get(dl_code) if dl_code else None
        days_to_deadline = None
        deadline_display = None
        recommended_by = None

        if dl:
            dl_date = _get_deadline_date(dl, today)
            days_to_deadline = (dl_date - today).days
            deadline_display = _deadline_display(dl_date)
            # Recommend acting 2 months before deadline
            rec = dl_date - timedelta(days=60)
            recommended_by = rec.strftime("%Y-%m-%d") if rec > today else today.strftime("%Y-%m-%d")

            if days_to_deadline < 0:
                urgency_mult = 0.5   # overdue ג€” damage done, lower priority
            elif days_to_deadline < 30:
                urgency_mult = 3.0
            elif days_to_deadline < 60:
                urgency_mult = 2.0
            elif days_to_deadline < 90:
                urgency_mult = 1.5
            else:
                urgency_mult = 1.0
        else:
            urgency_mult = 1.0

        score = annual_value * urgency_mult * consec_factor
        label, color = _priority_label(score)

        # Build "why high priority" explanations
        reasons = []
        if consecutive >= 2:
            reasons.append(f"׳—׳•׳¡׳¨ ׳§׳™׳™׳ {consecutive} ׳—׳•׳“׳©׳™׳ ׳¨׳¦׳•׳₪׳™׳")
        if annual_value >= 100_000:
            reasons.append(f"׳©׳•׳•׳™ ׳©׳ ׳×׳™ ׳’׳‘׳•׳”: ג‚×{annual_value:,.0f}")
        if days_to_deadline is not None:
            if days_to_deadline < 0:
                reasons.append(f"׳”׳׳•׳¢׳“ ׳”׳׳—׳¨׳•׳ ׳¢׳‘׳¨ ({deadline_display})")
            elif days_to_deadline < 60:
                reasons.append(f"׳׳•׳¢׳“ ׳”׳’׳©׳” ׳§׳¨׳•׳‘: {deadline_display}")
            else:
                reasons.append(f"׳׳•׳¢׳“ ׳”׳’׳©׳”: {deadline_display}")
        if lost_so_far > 0:
            reasons.append(f"׳›׳‘׳¨ ׳”׳₪׳¡׳“׳×: ג‚×{lost_so_far:,.0f}")

        total_lost_all += lost_so_far

        priorities.append({
            "position_type": pos.id,
            "position_name": pos.type,
            "priority_score": round(score),
            "priority_label": label,
            "priority_color": color,
            "annual_value": round(annual_value),
            "monthly_value": round(pos.monthly_gap_value),
            "gap": pos.gap,
            "consecutive_months": consecutive,
            "lost_so_far": round(lost_so_far),
            "days_to_deadline": days_to_deadline,
            "deadline_display": deadline_display,
            "urgency_multiplier": urgency_mult,
            "consecutive_factor": consec_factor,
            "why_high_priority": reasons,
            "recommended_action": dl.how_to_submit.split("\n")[0] if dl else "׳₪׳ ׳” ׳׳׳©׳¨׳“ ׳”׳—׳™׳ ׳•׳",
            "recommended_by": recommended_by,
            "deadline_code": dl_code,
        })

    priorities.sort(key=lambda p: -p["priority_score"])
    for i, p in enumerate(priorities):
        p["priority_rank"] = i + 1

    total_savable = total_annual - total_lost_all

    return {
        "municipality_id": municipality_id,
        "month": month,
        "priorities": priorities,
        "summary": {
            "total_annual_value": round(total_annual),
            "total_lost_so_far": round(total_lost_all),
            "total_savable": round(max(0, total_savable)),
            "count": len(priorities),
        },
    }


# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
# Startup initializer ג€” call from main.py
# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

def init_deadlines(db: Session):
    """Create tables and seed deadline data. Call once at startup."""
    _create_deadlines_tables()
    seed_ministry_deadlines(db)


# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
# Public helper ג€” save gap history (called from positions.py)
# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

def save_gap_history(db: Session, municipality_id: int, month: str, positions: list):
    """
    Auto-save gap history for all positions.
    Called after every positions analysis.
    """
    try:
        for pos in positions:
            existing = db.query(PositionGapsHistory).filter(
                PositionGapsHistory.municipality_id == municipality_id,
                PositionGapsHistory.month == month,
                PositionGapsHistory.position_type == pos.id,
            ).first()
            if existing:
                existing.current_value = pos.current
                existing.entitled_value = pos.entitled
                existing.gap_value = max(0, pos.gap)
                existing.gap_amount = pos.annual_gap_value / 12 if pos.gap > 0 else 0
            else:
                db.add(PositionGapsHistory(
                    municipality_id=municipality_id,
                    month=month,
                    position_type=pos.id,
                    current_value=pos.current,
                    entitled_value=pos.entitled,
                    gap_value=max(0, pos.gap),
                    gap_amount=pos.annual_gap_value / 12 if pos.gap > 0 else 0,
                ))
        db.commit()
    except Exception as e:
        logger.warning(f"Could not save gap history: {e}")
        db.rollback()


# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
# Admin endpoint ג€” get all municipalities deadline status
# ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€

@router.get("/api/deadlines/admin/overview")
async def get_admin_deadline_overview(
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Admin: upcoming deadlines with per-municipality submission status."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="׳’׳™׳©׳” ׳׳׳“׳׳™׳ ׳‘׳׳‘׳“")

    today = date.today()
    academic_year = _get_academic_year(today)

    # Deadlines in the next 120 days
    deadlines = db.query(AppDeadline).all()
    upcoming_deadlines = []
    for dl in deadlines:
        dl_date = _get_deadline_date(dl, today)
        days = (dl_date - today).days
        if -30 <= days <= 120:
            upcoming_deadlines.append((dl, dl_date, days))

    upcoming_deadlines.sort(key=lambda x: x[1])

    municipalities = db.query(Municipality).all()

    result = []
    for dl, dl_date, days in upcoming_deadlines:
        muni_statuses = []
        for muni in municipalities:
            app = db.query(ApplicationTracking).filter(
                ApplicationTracking.municipality_id == muni.id,
                ApplicationTracking.deadline_id == dl.id,
                ApplicationTracking.academic_year == academic_year,
            ).first()
            submitted = app and app.status in ("submitted", "approved")
            muni_statuses.append({
                "id": muni.id,
                "name": muni.name,
                "submitted": submitted,
                "status": app.status if app else "not_started",
                "reference_number": app.reference_number if app else None,
            })

        not_submitted = [m for m in muni_statuses if not m["submitted"]]

        result.append({
            "deadline_id": dl.id,
            "deadline_code": dl.code,
            "deadline_title": dl.title_hebrew,
            "deadline_date": dl_date.isoformat(),
            "deadline_display": _deadline_display(dl_date),
            "days_until": days,
            "urgency": _urgency(days),
            "municipalities": muni_statuses,
            "submitted_count": len(muni_statuses) - len(not_submitted),
            "not_submitted_count": len(not_submitted),
            "not_submitted_names": [m["name"] for m in not_submitted],
        })

    return {
        "academic_year": academic_year,
        "today": today.isoformat(),
        "upcoming_deadlines": result,
    }

