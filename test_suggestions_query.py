#!/usr/bin/env python3
"""
Direct test of the suggestions query without going through FastAPI.
"""
import sys
sys.path.insert(0, '.')

print("Step 1: Importing config...")
from backend.config import DATABASE_URL
print(f"  Database URL: {DATABASE_URL}")

print("Step 2: Importing engine and sessionmaker...")
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
print("  Success")

print("Step 3: Creating engine...")
engine = create_engine(DATABASE_URL, echo=False)
print("  Success")

print("Step 4: Creating SessionLocal...")
SessionLocal = sessionmaker(bind=engine)
print("  Success")

print("Step 5: Importing models...")
from backend.models.explanation_suggestion import ExplanationSuggestion, SuggestionStatus
print("  Success")

print("\nStep 6: Creating database session...")
db = SessionLocal()
print("  Session created")

try:
    print("\nStep 7: Querying pending suggestions...")
    query = db.query(ExplanationSuggestion).filter(
        ExplanationSuggestion.status == SuggestionStatus.PENDING
    )
    print(f"Query created: {query}")
    
    suggestions = query.order_by(ExplanationSuggestion.created_at.desc()).all()
    print(f"\n✅ Found {len(suggestions)} pending suggestions\n")
    
    for s in suggestions:
        print(f"Suggestion ID {s.id}:")
        print(f"  Status: {s.status}")
        print(f"  Suggested by ID: {s.suggested_by}")
        print()

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    print("Closing database session...")
    db.close()
    print("Done.")
