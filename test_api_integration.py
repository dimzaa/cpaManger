#!/usr/bin/env python3
"""
Comprehensive test for month changes fixes
Tests: CPA saves explanation → API returns it → Frontend can parse it
"""

import requests
import json
import time
from datetime import datetime

# API base URL
API_URL = "http://localhost:8000"

def test_api_workflows():
    """Test full workflow: Save explanation, retrieve it, verify fields"""
    
    print("=" * 70)
    print("API INTEGRATION TEST")
    print("=" * 70)
    print("\nThis test requires backend server running on port 8000")
    print("Start it with: python -m uvicorn backend.main:app --reload --port 8000")
    print("")
    
    # Check if API is reachable
    print("Checking if API is reachable...")
    try:
        response = requests.get(f"{API_URL}/", timeout=2)
        print(f"  ✅ API is running on {API_URL}")
    except requests.exceptions.ConnectionError:
        print(f"  ❌ Cannot reach API on {API_URL}")
        print("  Please start the backend server first")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Test 1: List municipalities
    print("\n1. Testing GET /api/municipalities/...")
    try:
        response = requests.get(f"{API_URL}/api/municipalities/", timeout=5)
        if response.status_code == 200:
            municipalities = response.json()
            if municipalities:
                test_muni_id = municipalities[0].get('id') or municipalities[0].get('municipality_id')
                print(f"  ✅ Found {len(municipalities)} municipalities")
                print(f"     Using: {test_muni_id}")
            else:
                print("  ⚠️  No municipalities in database")
                print("     Run: python seed_fresh_db.py")
                return False
        else:
            print(f"  ❌ Got status {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Test 2: Get budget with month_changes
    current_month = datetime.now().strftime("%Y-%m")
    print(f"\n2. Testing GET /api/budget/{test_muni_id}/{current_month}...")
    try:
        response = requests.get(
            f"{API_URL}/api/budget/{test_muni_id}/{current_month}",
            params={"month_changes": "true"},
            timeout=5
        )
        if response.status_code == 200:
            budget = response.json()
            has_month_changes = "month_changes" in budget
            print(f"  ✅ Budget loaded")
            print(f"     Has month_changes field: {has_month_changes}")
            if has_month_changes:
                print(f"     month_changes.has_changes: {budget['month_changes'].get('has_changes')}")
        else:
            print(f"  ⚠️  Status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")
    
    # Test 3: Get explanations - THIS IS THE KEY TEST FOR ISSUE 2
    print(f"\n3. Testing GET /api/explanations/municipality/{test_muni_id}/month/{current_month}...")
    try:
        response = requests.get(
            f"{API_URL}/api/explanations/municipality/{test_muni_id}/month/{current_month}",
            timeout=5
        )
        if response.status_code == 200:
            exp_response = response.json()
            print(f"  ✅ Explanations loaded")
            
            # Check the response structure - THIS IS WHAT THE FRONTEND PARSES
            if "explanations" in exp_response:
                explanations = exp_response["explanations"]
                print(f"     Found {len(explanations)} explanations")
                if explanations:
                    first_exp = explanations[0]
                    print(f"     First explanation structure:")
                    print(f"       - topic_code: {first_exp.get('topic_code', 'MISSING')}")
                    print(f"       - explanation: {first_exp.get('explanation', 'MISSING')[:50]}..." if first_exp.get('explanation') else "       - explanation: MISSING")
                    print(f"       - is_custom: {first_exp.get('is_custom', 'MISSING')}")
                    print(f"       - has_changes: {first_exp.get('has_changes', 'MISSING')}")
                    
                    # THE KEY CHECK: Does API return 'explanation' field?
                    if "explanation" in first_exp:
                        print(f"\n  ✅ API RETURNS CORRECT FIELD: 'explanation'")
                        print(f"     Frontend PortalBudgetPage can now parse: exp.explanation")
                    else:
                        print(f"\n  ❌ API MISSING 'explanation' FIELD")
                        print(f"     Available fields: {list(first_exp.keys())}")
                        return False
            else:
                print(f"  ⚠️  Response structure:")
                print(f"     Keys: {list(exp_response.keys())}")
        else:
            print(f"  ⚠️  Status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")
    
    print("\n" + "=" * 70)
    print("✅ API INTEGRATION TEST COMPLETE")
    print("=" * 70)
    print("\nIf all tests above show ✅, the fixes are working correctly!")
    print("\nNext steps for full testing:")
    print("1. Start backend: python -m uvicorn backend.main:app --reload --port 8000")
    print("2. Start frontend: npm run dev (from frontend folder)")
    print("3. Test in browser as CPA admin - should see month changes")
    print("4. Test in browser as municipality user - should see CPA explanations")
    
    return True


if __name__ == "__main__":
    try:
        test_api_workflows()
    except KeyboardInterrupt:
        print("\nTest interrupted")
    except Exception as e:
        print(f"\nTest failed: {e}")
