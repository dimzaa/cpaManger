#!/usr/bin/env python3
"""Test if the response can be JSON serialized."""
import sys
sys.path.insert(0, '.')

from backend.database import SessionLocal
from backend.models import User
import json

# Import the endpoint function
from backend.routes.budget import get_budget_for_month

db = SessionLocal()
admin_user = db.query(User).filter(User.email == "admin@example.com").first()

try:
    print("Calling get_budget_for_month...")
    result = get_budget_for_month(
        municipality_id=4,
        month="2026-03",
        current_user=admin_user,
        db=db
    )
    print(f"✓ Function returned successfully")
    
    print("\nAttempting to JSON serialize the response...")
    json_str = json.dumps(result, default=str)
    print(f"✓ JSON serialization successful")
    print(f"  Response size: {len(json_str)} bytes")
    
    # Try to parse it back
    print("\nParsing JSON back...")
    parsed = json.loads(json_str)
    print(f"✓ JSON parsing successful")
    
except Exception as e:
    print(f"✗ ERROR: {type(e).__name__}")
    print(f"  {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
