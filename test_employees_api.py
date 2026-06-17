"""
Test the POST /api/employees endpoint directly
"""

import requests
import json
from datetime import datetime

API = "http://127.0.0.1:8000/api"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

print("=" * 60)
print("🧪 TESTING POST /api/employees ENDPOINT")
print("=" * 60)

# Step 1: Login as admin
print("\n1️⃣ Login as admin...")
login_res = requests.post(
    f"{API}/auth/login",
    json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
)
if login_res.status_code != 200:
    print(f"❌ Login failed: {login_res.text}")
    exit(1)

token = login_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"✅ Admin logged in, token: {token[:20]}...")

# Step 2: Get municipalities
print("\n2️⃣ Fetching municipalities...")
mun_res = requests.get(f"{API}/municipalities", headers=headers)
if mun_res.status_code != 200:
    print(f"❌ Failed to get municipalities: {mun_res.text}")
    exit(1)

municipalities = mun_res.json()
print(f"✅ Found {len(municipalities)} municipalities:")
for mun in municipalities[:3]:
    print(f"   - ID: {mun['id']}, Name: {mun['name']}")

if not municipalities:
    print("⚠️  No municipalities found!")
    exit(1)

first_mun_id = municipalities[0]['id']

# Step 3: POST to create employee with unique email
print("\n3️⃣ Creating employee...")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[-6:]
unique_email = f"employee_{timestamp}@test.com"

new_employee = {
    "email": unique_email,
    "password": "testpass123",
    "first_name": "Test",
    "last_name": "Employee",
    "municipality_ids": [first_mun_id]
}

print(f"   Request body: {json.dumps(new_employee, indent=2)}")

employee_res = requests.post(
    f"{API}/employees",
    headers=headers,
    json=new_employee
)

print(f"   Status code: {employee_res.status_code}")
print(f"   Response: {employee_res.text}")

if employee_res.status_code in [200, 201]:
    response = employee_res.json()
    emp_data = response.get('data') if isinstance(response, dict) and 'data' in response else response
    print(f"✅ Employee created successfully!")
    print(f"   ID: {emp_data.get('id')}")
    print(f"   Email: {emp_data.get('email')}")
    print(f"   Name: {emp_data.get('first_name')} {emp_data.get('last_name')}")
    print(f"   Municipalities: {emp_data.get('municipality_ids')}")
else:
    print(f"❌ Failed to create employee")
    print(f"   Status: {employee_res.status_code}")
    print(f"   Error: {employee_res.json()}")

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
