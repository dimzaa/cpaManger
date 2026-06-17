"""
Create municipality user for עירית כפר קרע (10406544)
"""
import sys
sys.path.insert(0, '/Users/zahal/OneDrive/cpa')

from backend.database import SessionLocal
from backend.models.user import User, UserRole
from backend.models.municipality import Municipality
from backend.services.auth import AuthService

db = SessionLocal()

# Find the municipality
municipality = db.query(Municipality).filter(Municipality.code == '10406544').first()

if not municipality:
    print("❌ Municipality 10406544 not found")
    db.close()
    sys.exit(1)

print(f"✅ Found municipality: {municipality.name}")

# Check if user already exists
existing_user = db.query(User).filter(User.email == 'user-10406544@example.com').first()

if existing_user:
    print(f"✅ User already exists: {existing_user.email}")
    db.close()
    sys.exit(0)

# Create the municipality user
password = "password123"
hashed_password = AuthService.hash_password(password)

new_user = User(
    email='user-10406544@example.com',
    hashed_password=hashed_password,
    role=UserRole.MUNICIPALITY,
    municipality_id=municipality.id,
    first_name='עובד',
    last_name='עירית כפר קרע',
    is_active=True
)

db.add(new_user)
db.commit()

print(f"\n✅ Created municipality user:")
print(f"   Email: user-10406544@example.com")
print(f"   Password: {password}")
print(f"   Municipality: {municipality.name}")
print(f"   Role: municipality")

db.close()
