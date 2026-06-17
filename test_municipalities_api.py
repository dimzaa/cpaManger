"""
Test the GET /api/municipalities endpoint
"""

import requests
import json

API = "http://127.0.0.1:8000/api"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

print("=" * 70)
print("🧪 TESTING GET /api/municipalities ENDPOINT")
print("=" * 70)

# Step 1: Login to get token
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
print(f"✅ Logged in, token: {token[:30]}...")

# Step 2: Test without trailing slash
print("\n2️⃣ Testing GET /api/municipalities (no trailing slash)...")
res1 = requests.get(f"{API}/municipalities", headers=headers)
print(f"   Status: {res1.status_code}")
print(f"   Response type: {type(res1.json())}")
print(f"   Response: {json.dumps(res1.json(), ensure_ascii=False, indent=2)[:500]}")

# Step 3: Test with trailing slash
print("\n3️⃣ Testing GET /api/municipalities/ (with trailing slash)...")
res2 = requests.get(f"{API}/municipalities/", headers=headers)
print(f"   Status: {res2.status_code}")
print(f"   Response type: {type(res2.json())}")
print(f"   Response: {json.dumps(res2.json(), ensure_ascii=False, indent=2)[:500]}")

# Step 4: Test without auth
print("\n4️⃣ Testing GET /api/municipalities without auth...")
res3 = requests.get(f"{API}/municipalities")
print(f"   Status: {res3.status_code}")
print(f"   Response: {res3.text[:200]}")

print("\n" + "=" * 70)
print("Summary:")
print(f"  With auth (no slash): {res1.status_code}")
print(f"  With auth (with slash): {res2.status_code}")
print(f"  Without auth: {res3.status_code}")
print("=" * 70)
