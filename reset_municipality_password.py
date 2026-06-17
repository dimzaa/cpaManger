"""
Reset password for municipality user
"""
import sys
sys.path.insert(0, '/Users/zahal/OneDrive/cpa')

from backend.database import SessionLocal
from backend.models.user import User
from backend.services.auth import AuthService

db = SessionLocal()

# Check if user exists
user = db.query(User).filter(User.email == 'user-10406544@example.com').first()

if not user:
    print("❌ User user-10406544@example.com NOT FOUND in database")
    db.close()
    sys.exit(1)

print(f"✅ User found:")
print(f"   Email: {user.email}")
print(f"   Role: {user.role}")
print(f"   Municipality ID: {user.municipality_id}")
print(f"   Active: {user.is_active}")

# Reset password
new_password = "password123"
hashed = AuthService.hash_password(new_password)
user.hashed_password = hashed
db.commit()

print(f"\n✅ Password reset to: {new_password}")
print(f"\n🔑 Login with:")
print(f"   Email: user-10406544@example.com")
print(f"   Password: {new_password}")

db.close()
