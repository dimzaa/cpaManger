#!/usr/bin/env python3
"""Test the API endpoint."""
import sys
sys.path.insert(0, '.')

import requests
import json

# Test server is running
print("Testing API endpoints...")
BASE_URL = "http://localhost:8000"

# First, login to get a token
print("\n1. Login as admin...")
login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"email": "admin@example.com", "password": "admin123"}
)
print(f"Status: {login_response.status_code}")
if login_response.status_code != 200:
    print(f"Response: {login_response.text}")
    sys.exit(1)

login_data = login_response.json()
token = login_data.get('access_token')
print(f"Token: {token[:20]}...")

# Test the pending suggestions endpoint
print("\n2. Getting pending suggestions...")
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

response = requests.get(
    f"{BASE_URL}/api/suggestions/pending",
    headers=headers
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    data = response.json()
    print(f"\n✅ Success! Found {len(data)} pending suggestions")
    for suggestion in data:
        print(f"  - ID: {suggestion.get('id')}, Type: {suggestion.get('suggestion_type')}, By: {suggestion.get('suggester_name')}")
else:
    print(f"\n❌ Error: {response.status_code}")
    print(f"Response: {response.text}")
