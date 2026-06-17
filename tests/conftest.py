"""
Shared fixtures and configuration for all backend tests.

Uses SQLite in-memory database to keep tests isolated and fast.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app
from backend.models.user import User, UserRole
from backend.models.municipality import Municipality
from backend.models.monthly_run import MonthlyRun
from backend.services.auth import AuthService

# ── In-memory SQLite for tests ─────────────────────────────────────────────
# Use shared-cache URI so all connections in the same process see the same DB
TEST_DATABASE_URL = "sqlite:///file::memory:?cache=shared&uri=true"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False, "uri": True},
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create fresh tables for each test, drop them after."""
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Test client with DB override wired in."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Seed helpers ────────────────────────────────────────────────────────────

@pytest.fixture
def admin_user(db):
    user = User(
        email="admin@test.com",
        hashed_password=AuthService.hash_password("AdminPass1"),
        first_name="Admin",
        last_name="Test",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def municipality_record(db):
    muni = Municipality(
        name="עיריית בדיקה",
        code="TEST01",
        login_email="muni@test.com",
    )
    db.add(muni)
    db.commit()
    db.refresh(muni)
    return muni


@pytest.fixture
def municipality_user(db, municipality_record):
    user = User(
        email="muni@test.com",
        hashed_password=AuthService.hash_password("MuniPass1"),
        first_name="Muni",
        last_name="User",
        role=UserRole.MUNICIPALITY,
        municipality_id=municipality_record.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def employee_user(db, municipality_record):
    user = User(
        email="emp@test.com",
        hashed_password=AuthService.hash_password("EmpPass12"),
        first_name="Emp",
        last_name="Worker",
        role=UserRole.EMPLOYEE,
        municipality_id=municipality_record.id,
        is_active=True,
        municipalities_assigned=[municipality_record],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_token(user: User) -> str:
    return AuthService.create_token(
        user_id=user.id,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else user.role,
        municipality_id=getattr(user, "municipality_id", None),
    )


@pytest.fixture
def admin_token(admin_user):
    return make_token(admin_user)


@pytest.fixture
def muni_token(municipality_user):
    return make_token(municipality_user)


@pytest.fixture
def emp_token(employee_user):
    return make_token(employee_user)


@pytest.fixture
def auth_headers_admin(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def auth_headers_muni(muni_token):
    return {"Authorization": f"Bearer {muni_token}"}


@pytest.fixture
def auth_headers_emp(emp_token):
    return {"Authorization": f"Bearer {emp_token}"}
