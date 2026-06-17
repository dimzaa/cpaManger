"""
SQLAlchemy model for ingestion_warnings table.

Captures parser-level reconciliation anomalies so the admin UI can
surface them without grepping stdout. Every time parse_zip decides to
fall back to CHESHBONIT for a code (because the detail file didn't
tie out), or an additive-closure succeeds, or a formula-input file
fails to parse, a row lands here.

Severities:
  * info     — additive tie-out succeeded (expected, but useful trail)
  * warn     — a detail file was skipped for one code, CHESHBONIT used
  * error    — a whole file failed to parse

Categories (used by the UI to filter / group):
  * tie_out_mismatch         — detail sum ≠ CHESHBONIT per code (warn)
  * additive_closure         — detail + aux tied out after combining (info)
  * additive_closure_failed  — detail + aux still doesn't equal CHESHBONIT (warn)
  * file_parse_error         — detail/aux CSV unreadable or malformed (error)
  * formula_input_error      — ICHLUSKITOT/MISROT/MISROTGY/HASMASLULIM fail (error)
  * empty_detail / empty_aux — file present but produced 0 rows (warn)
  * missing_file             — expected aux/formula file absent (info)
  * unknown_code             — CHESHBONIT has a קוד נושא with no metadata
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from backend.database import Base


class IngestionWarning(Base):
    __tablename__ = "ingestion_warnings"

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

    severity = Column(String(16), nullable=False, index=True)  # info|warn|error
    category = Column(String(32), nullable=False, index=True)

    # What code/file triggered it
    file_type = Column(String(32), nullable=True)  # MUTAVIM, SHARATIM, etc.
    topic_code = Column(String(10), nullable=True, index=True)

    # Reconciliation deltas (nullable — not every warning carries numbers)
    detail_sum = Column(Float, nullable=True)
    aux_sum = Column(Float, nullable=True)
    cheshbonit_sum = Column(Float, nullable=True)
    delta = Column(Float, nullable=True)

    message = Column(String(500), nullable=False)

    created_at = Column(DateTime, server_default=func.now())

    monthly_run = relationship("MonthlyRun")
    municipality = relationship("Municipality")

    def __repr__(self):
        return (
            f"<IngestionWarning {self.severity} {self.category} "
            f"code={self.topic_code} file={self.file_type}>"
        )
