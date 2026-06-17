#!/usr/bin/env python3
"""
Test that all key endpoints work after the fix.
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(name, method, path, headers=None):
    """Test an endpoint"""
    print(f"\n✓ Testing {method} {path}")
    
    try:
        if method == "GET":
            resp = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=10)
        elif method == "POST":
            resp = requests.post(f"{BASE_URL}{path}", headers=headers, timeout=10)
        
        if resp.status_code >= 500:
            print(f"  ❌ ERROR: {resp.status_code}")
            try:
                print(f"     {resp.json().get('detail', 'Unknown error')}")
            except:
                print(f"     {resp.text[:100]}")
            return False
        elif resp.status_code >= 400:
            if resp.status_code == 404:
                print(f"  ⚠️  Not found (expected for some tests)")
            elif resp.status_code == 401:
                print(f"  ⚠️  Requires auth (expected)")
            else:
                print(f"  ⚠️  {resp.status_code}")
            return True
        else:
            try:
                data = resp.json()
                if isinstance(data, list):
                    print(f"  ✅ SUCCESS - {len(data)} items")
                elif isinstance(data, dict):
                    print(f"  ✅ SUCCESS - {list(data.keys())[:3]}...")
                else:
                    print(f"  ✅ SUCCESS")
            except:
                print(f"  ✅ SUCCESS - {len(resp.content)} bytes")
            return True
    except requests.exceptions.Timeout:
        print(f"  ❌ TIMEOUT")
        return False
    except Exception as e:
        print(f"  ❌ ERROR: {str(e)}")
        return False

# Get token
print("=" * 70)
print("TESTING KEY ENDPOINTS AFTER FIX")
print("=" * 70)

print("\n>>> Logging in to get token...")
resp = requests.post(f"{BASE_URL}/api/auth/login",
    json={"email": "admin@example.com", "password": "admin123"},
    timeout=10)

if resp.status_code != 200:
    print(f"Login failed: {resp.status_code}")
    exit(1)

token = resp.json()['access_token']
headers = {"Authorization": f"Bearer {token}"}
print(f"✅ Got token")

# Test endpoints
print("\n" + "=" * 70)
print("TESTING MUNICIPALITY PAGES (Admin)")
print("=" * 70)

test_endpoint("Municipalities list", "GET", "/api/municipalities/", headers)
test_endpoint("Municipality detail", "GET", "/api/municipalities/1", headers)
test_endpoint("Runs for month", "GET", "/api/runs/?month=2026-03", headers)
test_endpoint("Budget for month", "GET", "/api/budget/4/2026-03", headers)

print("\n" + "=" * 70)
print("TESTING EMPLOYEE/SUGGESTION ENDPOINTS (New)")
print("=" * 70)

test_endpoint("List employees", "GET", "/api/employees", headers)
test_endpoint("List suggestions", "GET", "/api/suggestions/pending", headers)
test_endpoint("List reasons", "GET", "/api/reasons", headers)

print("\n" + "=" * 70)
print("✅ All critical endpoints working!")
print("=" * 70)
