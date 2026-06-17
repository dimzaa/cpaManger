"""
Authentication guards and middleware for protecting routes.

Provides FastAPI dependencies for:
- require_login: Any authenticated user
- require_admin: Admin user only
- require_municipality_access: Ensure user can access specific municipality
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.models.user import User, UserRole
from backend.services.auth import AuthService

security = HTTPBearer()


# Alias for convenience (same as require_login)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user.
    
    This is an alias for require_login, used in routes that need the current user.
    """
    token = credentials.credentials
    
    try:
        payload = AuthService.verify_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user_id = int(sub)
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


def require_login(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Require user to be logged in.
    
    Returns the current User object from the database.
    
    Usage:
        @router.get("/protected")
        def protected_route(current_user: User = Depends(require_login)):
            return {"message": f"Hello {current_user.email}"}
    
    Raises:
        HTTPException 401: If token invalid or expired
    """
    token = credentials.credentials
    
    try:
        payload = AuthService.verify_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user_id = int(sub)
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    
    return user


def require_admin(
    current_user: User = Depends(require_login)
) -> User:
    """
    Require user to be an admin.
    
    Returns the current User if they are an admin.
    
    Usage:
        @router.post("/upload")
        def upload_file(current_user: User = Depends(require_admin)):
            # Only admins can reach here
            pass
    
    Raises:
        HTTPException 403: If user is not an admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    return current_user


def require_employee(
    current_user: User = Depends(require_login)
) -> User:
    """
    Require user to be an employee.
    
    Returns the current User if they are an employee (or admin).
    Employees can suggest explanations for municipalities they're assigned to.
    
    Usage:
        @router.post("/suggestions")
        def submit_suggestion(current_user: User = Depends(require_employee)):
            # Only employees (and admins) can reach here
            pass
    
    Raises:
        HTTPException 403: If user is not an employee
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.EMPLOYEE]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee access required",
        )
    
    return current_user


def require_municipality_access(
    municipality_id: int,
    current_user: User = Depends(require_login)
) -> User:
    """
    Require user to be accessing their assigned municipality data.
    
    Admins can access any municipality.
    Municipality users can only access their own municipality.
    Employees can only access municipalities they're assigned to.
    
    Usage in a route with path parameter:
        @router.get("/budget/{municipality_id}")
        def get_budget(
            municipality_id: int,
            current_user: User = Depends(require_login),
            db: Session = Depends(get_db)
        ):
            require_municipality_access(municipality_id, current_user)
            # Endpoint logic here
    
    Args:
        municipality_id: The municipality being accessed
        current_user: The authenticated user
        
    Returns:
        The current user if access is allowed
        
    Raises:
        HTTPException 403: If user cannot access this municipality
    """
    if current_user.role == UserRole.ADMIN:
        # Admins can access everything
        return current_user
    
    if current_user.role == UserRole.MUNICIPALITY:
        # Municipality users can only access their own municipality
        if current_user.municipality_id != municipality_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this municipality's data",
            )
        return current_user
    
    if current_user.role == UserRole.EMPLOYEE:
        # Employees can only access municipalities they're assigned to
        assigned_ids = [m.id for m in current_user.municipalities_assigned]
        if municipality_id not in assigned_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this municipality",
            )
        return current_user
    
    # Unknown role
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Unknown user role",
    )
