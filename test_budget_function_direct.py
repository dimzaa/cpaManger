#!/usr/bin/env python3
"""Test the get_budget_for_month function directly."""
import sys
sys.path.insert(0, '.')

from backend.database import SessionLocal
from backend.models import User
from sqlalchemy.orm import Session

# Import and run the endpoint function directly
from backend.routes.budget import get_budget_for_month

db = SessionLocal()
admin_user = db.query(User).filter(User.email == "admin@example.com").first()

try:
    print("Calling get_budget_for_month directly...")
    result = get_budget_for_month(
        municipality_id=4,
        month="2026-03",
        current_user=admin_user,
        db=db
    )
    print(f"✓ Success! Got result with {len(result.get('budget_lines', []))} lines")
    
except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}")
    print(f"Message: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
