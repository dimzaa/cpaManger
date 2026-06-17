"""
Authentication routes for login, registration, and token management.

Endpoints:
- POST /api/auth/register - Register a new user
- POST /api/auth/login - Login and get token
- GET /api/auth/me - Get current user info (requires authentication)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime

from backend.database import get_db
from backend.models.user import User, UserRole, AuditLog
from backend.services.auth import AuthService
from backend.utils.auth_guards import require_login

router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"],
)


# ========== SCHEMAS ==========

class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    first_name: str
    last_name: str
    municipality_id: Optional[int] = None


class UserLogin(BaseModel):
    """Schema for login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class UserResponse(BaseModel):
    """Schema for user response."""
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    municipality_id: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ========== ROUTES ==========

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user.
    
    Args:
        user_data: Registration data (email, password, name, municipality_id)
        db: Database session
        
    Returns:
        Created user info (without password)
        
    Raises:
        HTTPException 400: If email already exists
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Determine role based on municipality_id
    role = UserRole.ADMIN if user_data.municipality_id is None else UserRole.MUNICIPALITY
    
    # Create user
    hashed_password = AuthService.hash_password(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=role,
        municipality_id=user_data.municipality_id,
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login user and return JWT token.
    
    Args:
        credentials: Email and password
        db: Database session
        
    Returns:
        JWT token and user info
        
    Raises:
        HTTPException 401: If credentials invalid
    """
    # DEBUG: Check database state
    total_users = db.query(User).count()
    existing_user = db.query(User).filter(User.email == credentials.email).first()
    print(f"\n🔐 LOGIN DEBUG:")
    print(f"   Total users in database: {total_users}")
    print(f"   Searching for email: {credentials.email}")
    print(f"   User found: {existing_user is not None}")
    if existing_user:
        print(f"   User ID: {existing_user.id}, Role: {existing_user.role}, Active: {existing_user.is_active}")
    print()
    
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not AuthService.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create token
    token = AuthService.create_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        municipality_id=user.municipality_id
    )
    
    # Build user response with municipalities for employees
    user_response = {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "municipality_id": user.municipality_id,
    }
    
    # Add municipality_ids for employees
    if user.role == UserRole.EMPLOYEE:
        user_response["municipality_ids"] = [m.id for m in user.municipalities_assigned]
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_response
    }


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(require_login)
):
    """
    Get current user information.
    
    Requires valid JWT token in Authorization header.
    
    Args:
        current_user: Authenticated user from JWT token
        
    Returns:
        User information (without password)
        
    Raises:
        HTTPException 401: If not authenticated
    """
    return current_user


# ========== AUDIT LOGGING ==========

def log_action(
    db: Session,
    user_id: int,
    action: str,
    endpoint: str,
    method: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    status_code: Optional[int] = None,
    error_message: Optional[str] = None
):
    """
    Log an audit action.
    
    Args:
        db: Database session
        user_id: User who performed action
        action: Action name (e.g., "upload_file")
        endpoint: API endpoint (e.g., "POST /api/upload")
        method: HTTP method
        resource_type: Type of resource (e.g., "budget")
        resource_id: ID of resource
        status_code: HTTP status code
        error_message: Error message if action failed
    """
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        endpoint=endpoint,
        method=method,
        resource_type=resource_type,
        resource_id=resource_id,
        status_code=status_code,
        error_message=error_message,
    )
    
    db.add(audit_log)
    db.commit()
