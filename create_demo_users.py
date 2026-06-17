#!/usr/bin/env python3
"""
Script to create demo users and test authentication.

Creates:
1. Admin user (CPA) - can access everything
2-4. Municipality users for each municipality - can only access their own data
"""

from backend.database import SessionLocal, init_db
from backend.models.user import User, UserRole
from backend.models.municipality import Municipality
from backend.services.auth import AuthService
from datetime import datetime

def create_demo_users():
    """Create demo users for testing."""
    # Initialize database
    init_db()
    
    db = SessionLocal()
    
    try:
        print("="*60)
        print("🔧 CREATING DEMO USERS")
        print("="*60 + "\n")
        
        # Check if admin user already exists
        admin_user = db.query(User).filter(User.email == "admin@example.com").first()
        if admin_user:
            print("✅ Admin user already exists!")
            print(f"   Email: admin@example.com")
            print(f"   Role: {admin_user.role}")
        else:
            # Create admin user (ALWAYS, even if no municipalities)
            print("📝 Creating admin user...")
            admin_user = User(
                email="admin@example.com",
                hashed_password=AuthService.hash_password("admin123"),
                first_name="Admin",
                last_name="CPA",
                role=UserRole.ADMIN,
                municipality_id=None,
                is_active=True,
            )
            db.add(admin_user)
            db.flush()  # Flush to assign ID
            db.commit()  # Commit to database
            
            # Verify it was saved
            verify_user = db.query(User).filter(User.email == "admin@example.com").first()
            if verify_user:
                print("✅ Created admin user:")
                print(f"   Email: admin@example.com")
                print(f"   Password: admin123")
                print(f"   Role: ADMIN (CPA - can access everything)")
                print(f"   Database ID: {verify_user.id}")
            else:
                print("⚠️  Admin user creation may have failed - not found in database after commit")
        
        # Get municipalities (optional)
        municipalities = db.query(Municipality).all()
        
        if not municipalities:
            print("\nℹ️  No municipalities found in database.")
            print("   (Upload budget data first to create municipalities for municipality users)")
        else:
            print(f"\n📋 Found {len(municipalities)} municipalities:")
            for mun in municipalities:
                print(f"   - {mun.name} (ID: {mun.id}, Code: {mun.code})")
            
            # Create municipality users
            print(f"\n📝 Creating municipality users...")
            for municipality in municipalities:
                email = f"user-{municipality.code}@example.com".lower()
                
                # Check if user already exists
                existing_user = db.query(User).filter(User.email == email).first()
                if not existing_user:
                    user = User(
                        email=email,
                        hashed_password=AuthService.hash_password("password123"),
                        first_name=municipality.name,
                        last_name="Employee",
                        role=UserRole.MUNICIPALITY,
                        municipality_id=municipality.id,
                        is_active=True,
                    )
                    db.add(user)
            
            db.commit()
            
            print("✅ Created municipality users:")
            for municipality in municipalities:
                email = f"user-{municipality.code}@example.com".lower()
                print(f"   {email}")
                print(f"      Municipality: {municipality.name}")
                print(f"      Password: password123")
        
        print("\n" + "="*60)
        print("🧪 TESTING AUTHENTICATION")
        print("="*60 + "\n")
        
        # Test admin login
        print("1️⃣  Testing admin login...")
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if AuthService.verify_password("admin123", admin.hashed_password):
            print("   ✅ Admin password verified")
            token = AuthService.create_token(
                user_id=admin.id,
                email=admin.email,
                role=admin.role,
                municipality_id=admin.municipality_id
            )
            print(f"   ✅ JWT Token created: {token[:50]}...")
        else:
            print("   ❌ Admin password incorrect")
        
        # Test municipality user login (if any exist)
        mun_user = db.query(User).filter(User.role == UserRole.MUNICIPALITY).first()
        if mun_user:
            print(f"\n2️⃣  Testing municipality user login ({mun_user.email})...")
            if AuthService.verify_password("password123", mun_user.hashed_password):
                print("   ✅ Municipality password verified")
                token = AuthService.create_token(
                    user_id=mun_user.id,
                    email=mun_user.email,
                    role=mun_user.role,
                    municipality_id=mun_user.municipality_id
                )
                print(f"   ✅ JWT Token created: {token[:50]}...")
            else:
                print("   ❌ Municipality password incorrect")
        
        # Test disabled account (only if municipalities exist)
        if municipalities:
            # Check if disabled user already exists
            disabled = db.query(User).filter(User.email == "disabled@example.com").first()
            if not disabled:
                disabled_user = User(
                    email="disabled@example.com",
                    hashed_password=AuthService.hash_password("password123"),
                    first_name="Disabled",
                    last_name="User",
                    role=UserRole.MUNICIPALITY,
                    municipality_id=municipalities[0].id,
                    is_active=False,  # Disabled
                )
                db.add(disabled_user)
                db.commit()
            
            print(f"\n3️⃣  Testing disabled account (disabled@example.com)...")
            disabled = db.query(User).filter(User.email == "disabled@example.com").first()
            if not disabled.is_active:
                print("   ✅ Account correctly marked as disabled")
                print("   ℹ️  Login endpoint will reject this user")
        
        print("\n" + "="*60)
        print("✨ DEMO USERS CREATED SUCCESSFULLY!")
        print("="*60)
        
        # Final verification - show what's in the database
        print("\n📊 FINAL DATABASE VERIFICATION:")
        all_users = db.query(User).all()
        print(f"Total users in database: {len(all_users)}")
        for user in all_users:
            print(f"  - {user.email} (Role: {user.role}, Active: {user.is_active})")
        
        if not all_users:
            print("  ⚠️  WARNING: No users found in database!")
            print("  This may indicate a database connection or session issue.")
        
        print("\nNow test with curl:\n")
        print("Login as admin:")
        print('  curl -X POST http://localhost:8000/api/auth/login \\')
        print('    -H "Content-Type: application/json" \\')
        print('    -d \'\'{"email":"admin@example.com","password":"admin123"}\'\'')
        print("\nGet current user:")
        print('  curl http://localhost:8000/api/auth/me \\')
        print('    -H "Authorization: Bearer <TOKEN>"')
        print("\nOr use the API docs at: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"\n❌ Error creating demo users: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to show what's in the database even on error
        try:
            print("\n⚠️  Attempting to show database state after error...")
            all_users = db.query(User).all()
            print(f"Users in database: {len(all_users)}")
            for user in all_users:
                print(f"  - {user.email} (Role: {user.role})")
        except:
            print("Could not query database (it may not be initialized)")
    finally:
        db.close()

if __name__ == "__main__":
    create_demo_users()
