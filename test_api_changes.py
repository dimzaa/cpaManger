#!/usr/bin/env python3
"""
Test the budget API endpoint to verify changes are returned
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000"

# Test credentials for municipality user
TEST_USER = {
    "email": "user-10406544@example.com",
    "password": "password123"
}

try:
    # 1. Login to get JWT token
    print("🔐 Logging in...")
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=TEST_USER,
        timeout=5
    )
    login_response.raise_for_status()
    
    data = login_response.json()
    token = data.get("access_token")
    
    if not token:
        print(f"❌ No token in response: {data}")
        sys.exit(1)
    
    print(f"✅ Logged in successfully, token: {token[:20]}...")
    
    # 2. Get March 2026 budget data
    print("\n📊 Fetching March 2026 budget data...")
    headers = {"Authorization": f"Bearer {token}"}
    
    budget_response = requests.get(
        f"{BASE_URL}/api/budget/4/2026-03",  # municipality_id=4, month=2026-03
        headers=headers,
        timeout=10
    )
    budget_response.raise_for_status()
    
    budget_data = budget_response.json()
    
    print(f"✅ Got budget data!")
    print(f"   - Municipality: {budget_data['municipality']['name']}")
    print(f"   - Month: {budget_data['month']}")
    print(f"   - Invoice total: ₪{budget_data['invoice_total']:,.2f}")
    print(f"   - Balanced: {budget_data['is_balanced']}")
    print(f"   - Budget lines: {len(budget_data['budget_lines'])}")
    
    # 3. Check for month_changes
    if "month_changes" in budget_data:
        changes = budget_data["month_changes"]
        print(f"\n✅ MONTH CHANGES DETECTED!")
        print(f"   Previous month: {changes['previous_month']}")
        print(f"   Has changes: {changes['has_changes']}")
        
        print(f"\n   Changes by topic code:")
        for code, change in sorted(changes['changes_by_topic'].items()):
            print(f"\n      קוד {code} - {change['topic_name']}:")
            print(f"         Items: {change['prev_lines_count']} → {change['curr_lines_count']} ({change['items_change']:+d})")
            print(f"         Amount: ₪{change['prev_total']:,.2f} → ₪{change['curr_total']:,.2f}")
            print(f"         Change: ₪{change['amount_change']:+,.2f} ({change['amount_change_pct']:+.1f}%)")
    else:
        print("\n⚠️ No month_changes in response!")
        print("Available keys:", list(budget_data.keys()))
    
    print("\n✅ API test completed successfully!")

except requests.exceptions.ConnectionError:
    print("❌ Could not connect to backend at http://localhost:8000")
    print("   Make sure the backend server is running!")
    sys.exit(1)

except requests.exceptions.RequestException as e:
    print(f"❌ Request error: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"   Response: {e.response.text}")
    sys.exit(1)

except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {str(e)}")
    sys.exit(1)
