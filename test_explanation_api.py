"""
Test the explanations API endpoint
"""
import requests
import json

BACKEND_URL = "http://localhost:8000"
LOGIN_ENDPOINT = f"{BACKEND_URL}/api/auth/login"
EXPLANATION_ENDPOINT = f"{BACKEND_URL}/api/explanations/4/2026-03/3"  # municipality=4, month=2026-03, topic=3

# Login as municipality user
print("🔐 Logging in as municipality user...")
response = requests.post(
    LOGIN_ENDPOINT,
    json={
        "email": "user-10406544@example.com",
        "password": "password123"
    }
)

if response.status_code != 200:
    print(f"❌ Login failed: {response.status_code}")
    print(response.text)
    exit(1)

token = response.json()['access_token']
print(f"✅ Got auth token")

# Query explanation endpoint
print(f"\n📝 Querying explanation for topic code 3...")
headers = {"Authorization": f"Bearer {token}"}

response = requests.get(EXPLANATION_ENDPOINT, headers=headers)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Explanation query successful!")
    print(f"\n   Topic: {data.get('topic_name', 'N/A')}")
    print(f"   Explanation: {data.get('explanation', 'N/A')[:80]}...")
    print(f"   Is custom: {data.get('is_custom', False)}")
    print(f"   Is retro: {data.get('is_retro', False)}")
    print(f"   Has changes: {data.get('has_changes', False)}")
else:
    print(f"❌ Explanation query failed: {response.status_code}")
    print(f"   Response: {response.text}")
