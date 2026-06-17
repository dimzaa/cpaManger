"""
Test the budget API to ensure it can query the data with the correct month format
"""
import requests
import json

BACKEND_URL = "http://localhost:8000"
LOGIN_ENDPOINT = f"{BACKEND_URL}/api/auth/login"
BUDGET_ENDPOINT = f"{BACKEND_URL}/api/budget/4/2026-03"  # municipality_id=4, month=2026-03

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

# Login
print("🔐 Logging in...")
response = requests.post(
    LOGIN_ENDPOINT,
    json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
)

if response.status_code != 200:
    print(f"❌ Login failed: {response.status_code}")
    print(response.text)
    exit(1)

token = response.json()['access_token']
print(f"✅ Got auth token")

# Query budget for March 2026
print(f"\n📊 Querying budget for municipality 4, month 2026-03...")
headers = {"Authorization": f"Bearer {token}"}

response = requests.get(BUDGET_ENDPOINT, headers=headers)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Budget query successful!")
    print(f"\n   Municipality: {data['municipality']['name']}")
    print(f"   Month: {data['month']}")
    print(f"   Status: {data['status']}")
    print(f"   Invoice total: ₪{data['invoice_total']:,.2f}")
    print(f"   Breakdown total: ₪{data['breakdown_total']:,.2f}")
    print(f"   Is balanced: {data['is_balanced']}")
    print(f"   Budget lines count: {len(data['budget_lines'])}")
    
    if data['budget_lines']:
        print(f"\n   First budget line:")
        bl = data['budget_lines'][0]
        print(f"      Topic: {bl['budget_topic']}")
        print(f"      Amount: ₪{bl['amount']:,.2f}")
        print(f"      Current month: {bl['current_month']}")
        print(f"      Period month: {bl['period_month']}")
else:
    print(f"❌ Budget query failed: {response.status_code}")
    print(f"   Response: {response.text}")
