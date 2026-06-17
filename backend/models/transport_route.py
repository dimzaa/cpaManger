"""
SQLAlchemy model for transport_routes table.

Stores per-route transportation detail from HASMASLULIM. Each row = one
specific route (מספר מסלול) with company, vehicle, km, daily cost,
participation %, and calculated total. No הפרש column — this is current
state, not delta.

Used for route-level audit: "which 3 routes drove the ₪40K transportation
increase?" and vendor/vehicle-class analysis.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from backend.database import Base


class TransportRoute(Base):
    __tablename__ = "transport_routes"

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

    # Route identity
    route_number = Column(String(32), nullable=True, index=True)  # מספר מסלול
    route_type = Column(String(100), nullable=True)   # תיאור סוג מסלול (שכור/עצמי)
    payment_group = Column(String(100), nullable=True)  # תיאור קבוצה לתשלום
    period = Column(String(100), nullable=True)       # תיאור תקופת מסלול
    direction = Column(String(100), nullable=True)    # תיאור כיוון נסיעה

    # Who runs it
    company_code = Column(String(32), nullable=True, index=True)  # חברת הסעה
    company_name = Column(String(255), nullable=True)

    # What it serves
    topic_code = Column(String(10), nullable=False, index=True)   # קוד נושא (52/140)
    topic_name = Column(String(255), nullable=True)
    localities = Column(String(500), nullable=True)   # ישובים
    institutions = Column(String(500), nullable=True)  # מוסדות

    # Vehicle
    vehicle_code = Column(String(32), nullable=True)
    vehicle_type = Column(String(100), nullable=True)
    license_plate = Column(String(32), nullable=True)

    # Cost structure
    days = Column(Integer, nullable=True)           # ימי ביצוע
    vehicle_count = Column(Integer, nullable=True)  # כמות רכבים
    km_per_trip = Column(Float, nullable=True)      # קמ בנסיעה
    daily_cost = Column(Float, nullable=True)       # עלות יומית
    participation_pct = Column(Float, nullable=True)  # אחוז השתתפות
    vat_factor = Column(Float, nullable=True)       # מע''מ
    escalation = Column(Float, nullable=True)       # התייקרות מצטברת

    # Calculated amounts
    calculated_total = Column(Float, nullable=True)  # סכום מחושב

    # When this applies
    period_month = Column(Integer, nullable=True)   # חודש תחולה parsed
    period_year = Column(Integer, nullable=True)

    notes = Column(String(500), nullable=True)   # הערה

    created_at = Column(DateTime, server_default=func.now())

    monthly_run = relationship("MonthlyRun")
    municipality = relationship("Municipality")

    def __repr__(self):
        return (
            f"<TransportRoute {self.route_number} "
            f"code={self.topic_code} co={self.company_code} "
            f"total={self.calculated_total}>"
        )
