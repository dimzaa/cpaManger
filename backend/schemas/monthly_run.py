"""Pydantic schemas for MonthlyRun data."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MonthlyRunBase(BaseModel):
    month: str = Field(..., description="Month in YYYY-MM format")
    year: int = Field(..., description="Year as integer")


class MonthlyRunCreate(MonthlyRunBase):
    municipality_id: int
    file_name: Optional[str] = None


class MonthlyRun(MonthlyRunBase):
    id: int
    municipality_id: int
    uploaded_at: datetime
    file_name: Optional[str] = None

    status: str = Field(description="pending / processed / error")
    invoice_total: Optional[float] = None
    breakdown_total: Optional[float] = None
    is_balanced: bool
    difference: Optional[float] = None
    error_message: Optional[str] = None

    # Priority-1 dashboard aggregates
    regular_total: Optional[float] = None
    retro_positive_total: Optional[float] = None
    retro_negative_total: Optional[float] = None
    topics_count: Optional[int] = None
    lines_count: Optional[int] = None

    review_status: str = Field(default="pending")
    review_status_note: Optional[str] = None
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    reviewer_name: Optional[str] = None

    class Config:
        from_attributes = True


class MonthlyRunSummary(BaseModel):
    id: int
    municipality_id: int
    month: str
    year: int
    status: str
    is_balanced: bool
    invoice_total: Optional[float] = None
    breakdown_total: Optional[float] = None
    difference: Optional[float] = None
    has_retro: Optional[bool] = None
    retro_total: Optional[float] = None

    # Priority-1 dashboard aggregates
    regular_total: Optional[float] = None
    retro_positive_total: Optional[float] = None
    retro_negative_total: Optional[float] = None
    topics_count: Optional[int] = None
    lines_count: Optional[int] = None

    review_status: str = "pending"
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    reviewer_name: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True
