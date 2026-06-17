"""
Employee Management Routes

Admin endpoints for managing employee users and their municipality assignments.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

from backend.database import get_db
from backend.models.user import User, UserRole, employee_municipality_association
from backend.models.municipality import Municipality
from backend.utils.auth_guards import require_admin
from backend.services.auth import AuthService
from backend.services.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/employees", tags=["employees"])


# Pydantic schemas
class EmployeeCreate(BaseModel):
    """Schema for creating a new employee."""
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    municipality_ids: List[int]  # Municipalities assigned to this employee


class EmployeeUpdate(BaseModel):
    """Schema for updating an employee."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    municipality_ids: Optional[List[int]] = None


class EmployeeResponse(BaseModel):
    """Response schema for an employee."""
    id: int
    email: str
    first_name: str
    last_name: str
    is_active: bool
    created_by: Optional[int] = None
    created_at: datetime
    municipality_ids: List[int]
    suggestion_count: int = 0

    class Config:
        from_attributes = True


# ===== GET ENDPOINTS =====

@router.get("")
async def list_employees(
    municipality_id: Optional[int] = None,
    active_only: bool = True,
    include_test: bool = False,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    List all employees (admin only).
    
    Query params:
    - municipality_id: Filter employees assigned to this municipality
    - active_only: Only return active employees (default: True)
    - include_test: Include test/demo accounts (default: False)
    """
    try:
        query = db.query(User).filter(User.role == UserRole.EMPLOYEE)
        # Filter out test data unless explicitly requested by admin
        if not include_test or current_user.role != UserRole.ADMIN:
            query = query.filter(User.is_test == False)
        
        
        if active_only:
            query = query.filter(User.is_active == True)
        
        employees = query.order_by(User.created_at.desc()).all()
        
        # Filter by municipality if specified
        if municipality_id:
            employees = [
                e for e in employees
                if any(m.id == municipality_id for m in e.municipalities_assigned)
            ]
        
        # Build response manually
        result = []
        for e in employees:
            result.append({
                "id": e.id,
                "email": e.email,
                "first_name": e.first_name,
                "last_name": e.last_name,
                "is_active": e.is_active,
                "created_by": e.created_by,
                "created_at": e.created_at,
                "municipality_ids": [m.id for m in e.municipalities_assigned],
                "suggestion_count": len(e.suggestions_made) if hasattr(e, 'suggestions_made') else 0
            })
        
        return result
    except Exception as e:
        logger.error(f"Error listing employees: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing employees: {str(e)}"
        )


@router.get("/{employee_id}")
async def get_employee(
    employee_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get details for a specific employee (admin only).
    """
    try:
        employee = db.query(User).filter(
            User.id == employee_id,
            User.role == UserRole.EMPLOYEE
        ).first()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        return {
            "id": employee.id,
            "email": employee.email,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "is_active": employee.is_active,
            "created_by": employee.created_by,
            "created_at": employee.created_at,
            "municipality_ids": [m.id for m in employee.municipalities_assigned],
            "suggestion_count": len(employee.suggestions_made) if hasattr(employee, 'suggestions_made') else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting employee: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting employee: {str(e)}"
        )


# ===== POST ENDPOINTS =====

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_employee(
    data: EmployeeCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new employee user (admin only).
    
    The employee can then suggest explanations for their assigned municipalities.
    """
    try:
        # Check if email already exists
        existing = db.query(User).filter(User.email == data.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Verify municipalities exist
        municipalities = db.query(Municipality).filter(
            Municipality.id.in_(data.municipality_ids)
        ).all()
        
        if len(municipalities) != len(data.municipality_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more municipalities not found"
            )
        
        # Create user
        employee = User(
            email=data.email,
            hashed_password=AuthService.hash_password(data.password),
            role=UserRole.EMPLOYEE,
            first_name=data.first_name,
            last_name=data.last_name,
            is_active=True,
            created_by=current_user.id,
            municipalities_assigned=municipalities
        )
        
        db.add(employee)
        db.commit()
        db.refresh(employee)
        
        logger.info(f"Employee created by {current_user.email}: {data.email}")
        
        # Build response manually to avoid ORM issues
        return {
            "data": {
                "id": employee.id,
                "email": employee.email,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "is_active": employee.is_active,
                "created_by": employee.created_by,
                "created_at": employee.created_at,
                "municipality_ids": [m.id for m in municipalities],
                "suggestion_count": 0
            },
            "message": "Employee created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating employee: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating employee: {str(e)}"
        )


# ===== PATCH ENDPOINTS =====

@router.patch("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update an employee (admin only).
    
    Can change name, active status, and municipality assignments.
    """
    employee = db.query(User).filter(
        User.id == employee_id,
        User.role == UserRole.EMPLOYEE
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Update basic fields
    if data.first_name is not None:
        employee.first_name = data.first_name
    if data.last_name is not None:
        employee.last_name = data.last_name
    if data.is_active is not None:
        employee.is_active = data.is_active
    
    # Update municipality assignments
    if data.municipality_ids is not None:
        municipalities = db.query(Municipality).filter(
            Municipality.id.in_(data.municipality_ids)
        ).all()
        
        if len(municipalities) != len(data.municipality_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more municipalities not found"
            )
        
        employee.municipalities_assigned = municipalities
    
    db.commit()
    db.refresh(employee)
    
    logger.info(f"Employee updated by {current_user.email}: {employee.email}")
    
    return {
        "id": employee.id,
        "email": employee.email,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "is_active": employee.is_active,
        "created_by": employee.created_by,
        "created_at": employee.created_at,
        "municipality_ids": [m.id for m in employee.municipalities_assigned],
        "suggestion_count": len(employee.suggestions_made)
    }


# ===== DELETE ENDPOINTS =====

@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete an employee user (admin only).
    
    Note: This soft-deletes by marking is_active=False.
    """
    employee = db.query(User).filter(
        User.id == employee_id,
        User.role == UserRole.EMPLOYEE
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee.is_active = False
    db.commit()
    
    logger.info(f"Employee deactivated by {current_user.email}: {employee.email}")
    
    return None
