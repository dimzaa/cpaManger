"""
Test that mimics what the frontend does:
1. Login
2. Fetch employees
3. Fetch municipalities
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"
API = f"{BASE_URL}/api"

print("=" * 70)
print("🧪 FRONTEND SIMULATION TEST")
print("=" * 70)

# Step 1: Login
print("\n1️⃣ POST /api/auth/login")
login_res = requests.post(
    f"{API}/auth/login",
    json={"email": "admin@example.com", "password": "admin123"},
    headers={"Content-Type": "application/json"}
)
print(f"   Status: {login_res.status_code}")

if login_res.status_code != 200:
    print(f"❌ Login failed!")
    exit(1)

login_data = login_res.json()
token = login_data.get("access_token")
print(f"✅ Token received: {token[:40]}...")

headers = {"Authorization": f"Bearer {token}"}

# Step 2: Get employees
print("\n2️⃣ GET /api/employees (with token)")
emp_res = requests.get(f"{API}/employees", headers=headers)
print(f"   Status: {emp_res.status_code}")
print(f"   Response: {emp_res.text[:300]}")

if emp_res.status_code == 200:
    employees = emp_res.json()
    print(f"✅ Employees: {len(employees)} found")
    if isinstance(employees, list):
        for emp in employees[:2]:
            print(f"   - {emp.get('email')}")
    else:
        print(f"⚠️  Response is dict, not list: {json.dumps(employees, indent=2)[:200]}")
else:
    print(f"❌ Error fetching employees: {emp_res.status_code}")
    employees = []

# Step 3: Get municipalities
print("\n3️⃣ GET /api/municipalities (with token)")
mun_res = requests.get(f"{API}/municipalities", headers=headers)
print(f"   Status: {mun_res.status_code}")
municipalities = mun_res.json()
print(f"✅ Municipalities: {len(municipalities)} found")
for mun in municipalities:
    print(f"   - ID: {mun['id']}, Name: {mun['name']}, Code: {mun['code']}")

print("\n" + "=" * 70)
print("✅ Frontend should now work correctly!")
print(f"   - {len(employees)} employees loaded")
print(f"   - {len(municipalities)} municipalities in dropdown")
print("=" * 70)
