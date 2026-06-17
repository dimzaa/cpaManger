"""
Database connection and session management.

Uses SQLAlchemy with PostgreSQL.
Provides session management for dependency injection in FastAPI routes.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import DATABASE_URL

# Create SQLAlchemy engine
_connect_args = {"timeout": 30, "check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL logging
    pool_pre_ping=True,  # Verify connections are alive before using them
    connect_args=_connect_args,
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for all models
Base = declarative_base()


def get_db():
    """
    Dependency injection function for FastAPI routes.
    
    Provides a database session to each request.
    Usage in routes:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Create all tables in the database.
    
    Call this once at startup:
        from backend.database import init_db
        init_db()
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables initialized")


def drop_db():
    """
    Drop all tables from the database.
    
    ⚠️ WARNING: This deletes all data!
    Use only for testing/development.
    """
    Base.metadata.drop_all(bind=engine)
    print("⚠️  All database tables dropped")
