"""
Pydantic schemas for Municipality data.

Used for API request/response validation and serialization.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class MunicipalityBase(BaseModel):
    """Base schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Hebrew name of municipality")
    code: str = Field(..., min_length=1, max_length=10, description="Ministry code")
    login_email: Optional[str] = Field(None, description="Email for portal access")


class MunicipalityCreate(MunicipalityBase):
    """Schema for creating a new municipality."""
    pass


class MunicipalityUpdate(BaseModel):
    """Schema for updating municipality."""
    name: Optional[str] = Field(None, max_length=255)
    code: Optional[str] = Field(None, max_length=10)
    login_email: Optional[str] = Field(None)


class Municipality(MunicipalityBase):
    """Schema for reading municipality data. Includes ID and timestamps."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True  # Allow reading from ORM objects


class MunicipalityList(BaseModel):
    """Schema for listing municipalities."""
    id: int
    code: str
    name: str
    login_email: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
