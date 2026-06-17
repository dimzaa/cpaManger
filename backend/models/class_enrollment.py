"""
SQLAlchemy model for class_enrollments table.

Stores per-institution × per-class × per-month student counts from ICHLUSKITOT.
Doesn't carry amounts — these are formula inputs used to attribute budget
variance to enrollment changes ("class 10-3 went from 18 → 17 pupils, which
explains the code-3 drop").
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from backend.database import Base


class ClassEnrollment(Base):
    __tablename__ = "class_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(
        Integer,
        ForeignKey("monthly_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    municipality_id = Column(
        Integer, ForeignKey("municipalities.id"), nullable=False, index=True
    )

    # Source school
    institution_code = Column(String(32), nullable=False, index=True)
    institution_name = Column(String(255), nullable=True)

    # Class descriptor
    class_level = Column(Integer, nullable=True)   # כיתה (grade level)
    stream = Column(Integer, nullable=True)        # מקבילה (parallel class number)
    class_type = Column(String(100), nullable=True)  # תאור סוג כיתה

    # Capacity reference
    min_students = Column(Integer, nullable=True)
    max_students = Column(Integer, nullable=True)

    # Month (1=Sept, 2=Oct, …, 12=Aug — Israeli school year) and count
    school_year = Column(Integer, nullable=False, index=True)  # שנה
    month = Column(Integer, nullable=False, index=True)        # 1..12
    student_count = Column(Integer, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    monthly_run = relationship("MonthlyRun")
    municipality = relationship("Municipality")

    def __repr__(self):
        return (
            f"<ClassEnrollment inst={self.institution_code} "
            f"class={self.class_level}-{self.stream} "
            f"m={self.month} n={self.student_count}>"
        )
