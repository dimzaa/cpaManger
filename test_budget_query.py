#!/usr/bin/env python3
"""Test the budget query to find the error."""
import sys
sys.path.insert(0, '.')

from backend.database import SessionLocal
from backend.models import MonthlyRun, BudgetLine, Municipality
from backend.models.approved_explanation import ApprovedExplanation

db = SessionLocal()

try:
    print("Testing query for municipality 4, month 2026-03...")
    
    # Get municipality
    mun = db.query(Municipality).filter(Municipality.id == 4).first()
    print(f"✓ Got municipality: {mun}")
    
    # Get run
    run = db.query(MonthlyRun).filter(
        MonthlyRun.municipality_id == 4,
        MonthlyRun.month == "2026-03"
    ).first()
    print(f"✓ Got run: {run}")
    
    # Get budget lines
    if run:
        lines = db.query(BudgetLine).filter(BudgetLine.run_id == run.id).all()
        print(f"✓ Got {len(lines)} budget lines")
        
        # Try to get approved explanations - THIS IS WHERE THE ERROR LIKELY IS
        print("Attempting to query ApprovedExplanation...")
        explanations = db.query(ApprovedExplanation).filter(
            ApprovedExplanation.municipality_id == 4,
            ApprovedExplanation.month == "2026-03"
        ).all()
        print(f"✓ Got {len(explanations)} approved explanations")
        
except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}")
    print(f"Message: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
