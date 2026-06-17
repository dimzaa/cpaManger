#!/usr/bin/env python3
"""Test exact response structure."""
import sys
sys.path.insert(0, '.')

import requests
import json

BASE_URL = "http://localhost:8000"

# Login
login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"email": "admin@example.com", "password": "admin123"}
)
token = login_response.json().get('access_token')

# Get suggestions
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
response = requests.get(f"{BASE_URL}/api/suggestions/pending", headers=headers)

print("Full response object:")
print(f"  Status code: {response.status_code}")
print(f"  Headers: {dict(response.headers)}")
print(f"  Content-Type: {response.headers.get('content-type')}")

print("\nResponse JSON structure:")
data = response.json()
print(f"  Type: {type(data)}")
print(f"  Is list: {isinstance(data, list)}")
print(f"  Is dict: {isinstance(data, dict)}")
if isinstance(data, dict):
    print(f"  Keys: {list(data.keys())}")
if isinstance(data, list):
    print(f"  Length: {len(data)}")
    print(f"  First item: {json.dumps(data[0], indent=2, default=str)}")
else:
    print(f"  Content: {json.dumps(data, indent=2, default=str)}")
