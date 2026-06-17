#!/usr/bin/env python3
"""
Initialize fresh database with seed data for testing.
"""

print("Starting database seeding script...")

from backend.database import SessionLocal, init_db
import backend.models
from backend.models import Municipality, User, MonthlyRun, BudgetLine, UserRole
from backend.services.auth import AuthService
import json

# First ensure tables exist
print("Ensuring database tables exist...")
init_db()
print("Tables initialized")

db = SessionLocal()

try:
    # Check if already seeded
    existing_users = db.query(User).count()
    existing_munis = db.query(Municipality).count()
    
    print(f"Existing users: {existing_users}, Municipalities: {existing_munis}")
    
    if existing_users > 0 and existing_munis > 0:
        print("✓ Database already seeded")
        db.close()
        exit(0)
    
    print("\n📦 Seeding municipalities...")
    municipalities_data = [
        {"name": "עיריית נצרת", "code": "3000"},
        {"name": "מועצת עראבה", "code": "3100"},
        {"name": "עיריית אום אל פחם", "code": "3200"},
        {"name": "עירית כפר קרע", "code": "10406544"},
    ]
    
    for muni_data in municipalities_data:
        muni = Municipality(
            name=muni_data["name"],
            code=muni_data["code"].encode() if isinstance(muni_data["code"], str) else muni_data["code"]
        )
        db.add(muni)
    db.commit()
    print(f"✅ Created {len(municipalities_data)} municipalities")
    
    print("\n👥 Seeding users...")
    
    # Admin user
    admin = User(
        email="admin@example.com",
        hashed_password=AuthService.hash_password("admin123"),
        role=UserRole.ADMIN,
        first_name="Admin",
        last_name="User",
        is_active=True
    )
    db.add(admin)
    db.commit()
    print("✅ Created admin@example.com")
    
    # Municipality users (one for each municipality)
    municipalities = db.query(Municipality).all()
    print(f"Found {len(municipalities)} municipalities, creating users...")
    for i, muni in enumerate(municipalities):
        code = muni.code.decode() if isinstance(muni.code, bytes) else str(muni.code)
        muni_user = User(
            email=f"user-{code.lower()}@example.com",
            hashed_password=AuthService.hash_password("password123"),
            role=UserRole.MUNICIPALITY,
            municipality_id=muni.id,
            first_name=f"Municipality",
            last_name=f"User {i+1}",
            is_active=True
        )
        db.add(muni_user)
    db.commit()
    print(f"✅ Created {len(municipalities)} municipality users")
    
    print("\n✅ Database seeding complete!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()

