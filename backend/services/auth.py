"""
Authentication service for JWT token generation and validation.

Handles:
- Password hashing with bcrypt
- JWT token creation and verification
- User authentication
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from jose import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from backend.config import SECRET_KEY

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24  # Regular users
JWT_ADMIN_EXPIRATION_HOURS = 8  # Admin users get shorter expiration


class AuthService:
    """Handle authentication operations."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return pwd_context.hash(password[:72])
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password from database
            
        Returns:
            True if password matches
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_token(
        user_id: int,
        email: str,
        role: str,
        municipality_id: Optional[int] = None
    ) -> str:
        """
        Create a JWT token for a user.
        
        Args:
            user_id: User ID
            email: User email
            role: User role (admin or municipality)
            municipality_id: Municipality ID (for municipality users)
            
        Returns:
            JWT token string
        """
        expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "municipality_id": municipality_id,
            "exp": expiration,
            "iat": datetime.utcnow(),
        }
        
        token = jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def extract_user_from_token(token: str) -> Tuple[int, str, str]:
        """
        Extract user information from a token.
        
        Args:
            token: JWT token string
            
        Returns:
            Tuple of (user_id, email, role)
            
        Raises:
            HTTPException: If token is invalid
        """
        payload = AuthService.verify_token(token)
        user_id = int(payload.get("sub"))
        email = payload.get("email")
        role = payload.get("role")
        
        return user_id, email, role


# Type hint for token response
from typing import Tuple
