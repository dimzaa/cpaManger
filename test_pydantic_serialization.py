#!/usr/bin/env python3
"""
Test Pydantic serialization of the suggestion.
"""
import sys
sys.path.insert(0, '.')

from backend.config import DATABASE_URL
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.explanation_suggestion import ExplanationSuggestion, SuggestionStatus

print("Creating database session...")
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    print("\nQuerying suggestion...")
    suggestion = db.query(ExplanationSuggestion).filter(
        ExplanationSuggestion.status == SuggestionStatus.PENDING
    ).first()
    
    if suggestion:
        print(f"Found suggestion ID {suggestion.id}")
        print(f"  Suggestion dict: {suggestion.__dict__}")
        
        print("\nTrying to import SuggestionResponse...")
        from backend.routes.suggestions import SuggestionResponse, SuggestionDetailResponse
        
        print("Creating SuggestionResponse from ORM...")
        response = SuggestionResponse.model_validate(suggestion)
        print(f"✅ SuggestionResponse created: {response}")
        
        print("\nCreating SuggestionDetailResponse...")
        detail = SuggestionDetailResponse.model_validate(suggestion)
        print(f"✅ SuggestionDetailResponse created")
        
        print(f"\nAttempting to access suggester relationship...")
        suggester = suggestion.suggester
        print(f"Suggester: {suggester}")
        if suggester:
            print(f"  Email: {suggester.email}")
            print(f"  First name: {suggester.first_name}")
            print(f"  Last name: {suggester.last_name}")
        
        print("\nAttempting to serialize to dict...")
        detail.suggester_name = f"{suggester.first_name or ''} {suggester.last_name or ''}".strip() if suggester else "Unknown"
        print(f"✅ Serialized: {detail.model_dump()}")
    else:
        print("No pending suggestions found")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    db.close()
    print("\nDone.")
