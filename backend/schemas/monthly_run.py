"""
Pydantic schemas for MonthlyRun data.

Used for API request/response validation and serialization.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MonthlyRunBase(BaseModel):
    """Base schema with common fields."""
    month: str = Field(..., description="Month in YYYY-MM format")
    year: int = Field(..., description="Year as integer")


class MonthlyRunCreate(MonthlyRunBase):
    """Schema for creating a monthly run. Not typically used directly."""
    municipality_id: int
    file_name: Optional[str] = None


class MonthlyRun(MonthlyRunBase):
    """Schema for reading monthly run data."""
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
    review_status: str = Field(default="pending", description="pending / in_review / reviewed / flagged")
    review_status_note: Optional[str] = None
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    reviewer_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class MonthlyRunSummary(BaseModel):
    """Schema for run summary in lists."""
    id: int
    municipality_id: int  # Required for frontend to match runs to municipalities
    month: str
    year: int
    status: str
    is_balanced: bool
    invoice_total: Optional[float] = None
    breakdown_total: Optional[float] = None
    difference: Optional[float] = None
    has_retro: Optional[bool] = None   # Whether any budget lines are retro payments
    retro_total: Optional[float] = None  # Sum of retro payment amounts
    review_status: str = "pending"
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    reviewer_name: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True
