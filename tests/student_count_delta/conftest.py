"""Isolated conftest for the student-count delta tests.

Avoids importing ``backend.main`` (and by extension the full router stack)
so these tests run even when unrelated routes in the source tree are in a
truncated state. We only need the ORM models and SQLAlchemy.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
# Import the models we touch so ``Base.metadata`` knows about their tables.
from backend.models.monthly_run import MonthlyRun  # noqa: F401
from backend.models.budget_line import BudgetLine  # noqa: F401
from backend.models.municipality import Municipality


TEST_DATABASE_URL = "sqlite:///file::memory:?cache=shared&uri=true"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False, "uri": True},
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


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
