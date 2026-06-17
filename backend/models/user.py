"""
Authentication models for user management.

Stores user credentials, roles, and permissions.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

from backend.database import Base


# Many-to-many association table for employees assigned to municipalities
employee_municipality_association = Table(
    'employee_municipality_assignment',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('municipality_id', Integer, ForeignKey('municipalities.id'), primary_key=True)
)


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"  # CPA admin - can upload files, approve explanations, manage all municipalities
    EMPLOYEE = "employee"  # Employee - can suggest explanations for assigned municipalities
    MUNICIPALITY = "municipality"  # Municipality viewer - sees only their municipality budget (read-only)


class User(Base):
    """
    Represents a system user (CPA admin, employee, or municipality viewer).
    
    Attributes:
        id: Primary key
        email: Unique email address
        hashed_password: Bcrypt hashed password
        role: User role (admin, employee, or municipality)
        municipality_id: Main municipality (for non-employees) or NULL (for employees/admins)
        municipalities_assigned: List of municipalities (for employees only)
        first_name: User's first name
        last_name: User's last name
        is_active: Whether the account is active
        created_by: ID of admin who created this user (for audit trail)
        created_at: When the account was created
        last_login: When the user last logged in
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Role and permissions
    role = Column(String(20), default=UserRole.MUNICIPALITY)  # admin, employee, or municipality
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=True, index=True)  # For non-employees
    
    # Profile info
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Which admin created this user
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, nullable=True)
    is_test = Column(Boolean, default=False, index=True)  # Flag for test/demo accounts
    
    # Relationships
    municipality = relationship("Municipality", foreign_keys=[municipality_id], backref="municipality_viewers")
    municipalities_assigned = relationship(
        "Municipality",
        secondary=employee_municipality_association,
        backref="assigned_employees"
    )
    creator = relationship("User", remote_side=[id], foreign_keys=[created_by], backref="employees_created")
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"


class AuditLog(Base):
    """
    Audit log for tracking all API actions.
    
    Provides accountability and compliance tracking.
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Action details
    action = Column(String(100), nullable=False)  # e.g., "upload_file", "view_budget"
    endpoint = Column(String(255), nullable=False)  # e.g., "POST /api/upload"
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE
    
    # Resource accessed
    resource_type = Column(String(50), nullable=True)  # e.g., "budget", "municipality"
    resource_id = Column(Integer, nullable=True)
    
    # Request/response details
    status_code = Column(Integer, nullable=True)
    request_data = Column(String(1000), nullable=True)  # Sanitized request data
    error_message = Column(String(500), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, server_default=func.now(), index=True)
    
    # Relationship
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog id={self.id} user_id={self.user_id} action={self.action}>"
