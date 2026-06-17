#!/usr/bin/env python3
"""
Test key API endpoints to identify which ones are broken.
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def test_endpoint(method, path, headers=None, json_data=None):
    """Test a single endpoint"""
    url = f"{BASE_URL}{path}"
    print(f"\n{method} {path}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=5)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=json_data, timeout=5)
        else:
            return False
            
        print(f"   Status: {response.status_code}")
        
        if response.status_code >= 500:
            print(f"   ❌ SERVER ERROR")
            try:
                error = response.json()
                print(f"   Error: {error.get('detail', error)}")
            except:
                print(f"   {response.text[:200]}")
            return False
        elif response.status_code >= 400:
            print(f"   ⚠️  Client Error (expected for some tests)")
            try:
                error = response.json()
                print(f"   {error.get('detail', error)}")
            except:
                print(f"   {response.text[:200]}")
            return False
        else:
            print(f"   ✅ SUCCESS")
            try:
                data = response.json()
                if isinstance(data, dict):
                    print(f"   Keys: {list(data.keys())}")
                elif isinstance(data, list):
                    print(f"   Items: {len(data)}")
            except:
                print(f"   Data: {response.text[:100]}")
            return True
    except requests.exceptions.Timeout:
        print(f"   ❌ TIMEOUT")
        return False
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return False

def main():
    print("\n🧪 TESTING KEY API ENDPOINTS")
    print("="*70)
    
    # First, try to get a token
    print_section("STEP 1: Login to get token")
    
    test_endpoint("POST", "/api/auth/login", json_data={
        "email": "admin@example.com",
        "password": "admin123"
    })
    
    # Get token
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@example.com", "password": "admin123"},
            timeout=5
        )
        if response.status_code == 200:
            token = response.json().get('access_token')
            headers = {"Authorization": f"Bearer {token}"}
            print(f"   Token obtained: {token[:50]}...")
        else:
            print(f"   Failed to get token: {response.status_code}")
            headers = {}
    except Exception as e:
        print(f"   Error getting token: {e}")
        headers = {}
    
    # Test all endpoints
    print_section("STEP 2: Test municipalities endpoint")
    test_endpoint("GET", "/api/municipalities/", headers=headers)
    
    print_section("STEP 3: Test budget endpoint")
    test_endpoint("GET", "/api/budget/4/2026-03", headers=headers)
    
    print_section("STEP 4: Test runs endpoint")
    test_endpoint("GET", "/api/runs/?month=2026-03", headers=headers)
    
    print_section("STEP 5: Test municipality detail")
    test_endpoint("GET", "/api/municipalities/4", headers=headers)
    
    print("\n" + "="*70)
    print("Check above to see which endpoints are failing")
    print("="*70)

if __name__ == "__main__":
    main()
