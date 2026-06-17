"""
Pydantic schemas for BudgetLine data.

Used for API request/response validation and serialization.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BudgetLineBase(BaseModel):
    """Base schema with common fields."""
    budget_topic: str = Field(..., description="Hebrew budget topic name")
    topic_code: str = Field(..., description="Topic numeric code")
    amount: float = Field(..., gt=0, description="Amount in shekels")
    period_month: str = Field(..., description="Period month in YYYY-MM format (חודש תחולה)")
    current_month: str = Field(..., description="Current month in YYYY-MM format (חודש העלאה)")


class BudgetLineCreate(BudgetLineBase):
    """Schema for creating a budget line item."""
    run_id: int
    municipality_id: int
    line_type: Optional[str] = "regular"
    notes: Optional[str] = None


class BudgetLine(BudgetLineBase):
    """Schema for reading budget line data."""
    id: int
    run_id: int
    municipality_id: int
    line_type: str = Field(description="regular / retro / shortage / adjustment")
    is_retro: bool
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class BudgetLineResponse(BaseModel):
    """Schema for budget line in API responses."""
    id: int
    budget_topic: str
    topic_code: str
    amount: float
    period_month: str
    current_month: str
    line_type: str
    is_retro: bool
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True


class BudgetLineGrouped(BaseModel):
    """Schema for budget lines grouped by month/topic."""
    budget_topic: str
    topic_code: str
    amount: float
    line_type: str
    is_retro: bool
    notes: Optional[str] = None
    period_month: str
    
    class Config:
        from_attributes = True
