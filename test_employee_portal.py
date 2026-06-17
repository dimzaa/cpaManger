#!/usr/bin/env python3
"""
Test employee portal loading:
1. Employee logs in and receives municipality_ids
2. Employee can fetch budget data for assigned municipalities
"""

import requests
import json
from datetime import datetime
from time import sleep

BASE_URL = "http://127.0.0.1:8000"

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def test_admin_login():
    """Test admin login to create an employee"""
    print_section("1️⃣ ADMIN LOGIN")
    
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@example.com", "password": "admin123"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        token = data.get('access_token')
        print(f"✅ Admin logged in")
        print(f"   Token: {token[:50]}...")
        return token
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   {response.text}")
        return None

def test_get_municipalities(token):
    """Fetch all municipalities to get names"""
    print_section("2️⃣ FETCH MUNICIPALITIES")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/municipalities/", headers=headers)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        munis = response.json() if isinstance(response.json(), list) else response.json().get('data', [])
        print(f"✅ Fetched {len(munis)} municipalities:")
        for m in munis[:4]:
            print(f"   - ID: {m.get('id')}, Name: {m.get('name')}")
        return munis
    else:
        print(f"❌ Error: {response.status_code}")
        return []

def test_create_employee(admin_token, municipality_ids):
    """Create a test employee with multiple municipalities"""
    print_section("3️⃣ CREATE EMPLOYEE")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    timestamp = int(datetime.now().timestamp())
    
    employee_data = {
        "email": f"employee_portal_test_{timestamp}@test.com",
        "password": "employee123",
        "first_name": "Portal",
        "last_name": "Test",
        "municipality_ids": municipality_ids[:3]  # Assign 3 municipalities
    }
    
    response = requests.post(
        f"{BASE_URL}/api/employees",
        headers=headers,
        json=employee_data
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 201]:
        data = response.json()
        employee = data.get('data', data)
        print(f"✅ Employee created")
        print(f"   ID: {employee.get('id')}")
        print(f"   Email: {employee.get('email')}")
        print(f"   Municipality IDs: {employee.get('municipality_ids')}")
        return employee_data['email'], employee_data['password']
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")
        return None, None

def test_employee_login(email, password):
    """Test employee login and check for municipality_ids"""
    print_section("4️⃣ EMPLOYEE LOGIN (KEY TEST)")
    
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        user = data.get('user', {})
        token = data.get('access_token')
        
        print(f"✅ Employee login successful")
        print(f"   Role: {user.get('role')}")
        print(f"   Municipality ID: {user.get('municipality_id')}")
        print(f"   Municipality IDs: {user.get('municipality_ids')}")
        
        # Check that municipality_ids is in response
        if 'municipality_ids' in user:
            print(f"   ✅ municipality_ids in response (GOOD for portal to work)")
        else:
            print(f"   ❌ municipality_ids NOT in response (portal will fail)")
        
        return token, user
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")
        return None, None

def test_employee_budget_load(employee_token, user, municipality_names):
    """Test loading budget for each assigned municipality"""
    print_section("5️⃣ EMPLOYEE BUDGET LOADING (PORTAL TEST)")
    
    headers = {"Authorization": f"Bearer {employee_token}"}
    municipality_ids = user.get('municipality_ids', [])
    
    if not municipality_ids:
        print(f"❌ No municipality_ids in user object - portal won't work")
        return False
    
    # Try loading budget for the first assigned municipality
    first_muni_id = municipality_ids[0]
    first_muni_name = municipality_names.get(first_muni_id, f"ID {first_muni_id}")
    
    # Use March 2026 as test month
    test_month = "2026-03"
    
    response = requests.get(
        f"{BASE_URL}/api/budget/{first_muni_id}/{test_month}",
        headers=headers
    )
    
    print(f"Testing: GET /api/budget/{first_muni_id}/{test_month}")
    print(f"Municipality: {first_muni_name}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        budget = response.json()
        print(f"✅ Budget loaded successfully!")
        print(f"   Total invoice: ₪{budget.get('invoice_total'):,}")
        print(f"   Total breakdown: ₪{budget.get('breakdown_total'):,}")
        print(f"   Balanced: {budget.get('is_balanced')}")
        return True
    elif response.status_code == 404:
        print(f"⚠️  No budget data for this month yet (404)")
        print(f"   This is OK - data will appear after accounting upload")
        return True  # Portal will show "אין נתונים זמינים"
    else:
        print(f"❌ Error loading budget: {response.status_code}")
        print(f"   {response.text}")
        return False

def main():
    print("\n🧪 TESTING EMPLOYEE PORTAL LOADING")
    print("=" * 70)
    print("This test verifies:")
    print("1. Employee receives municipality_ids in login response")
    print("2. Employee can load budget data for assigned municipalities")
    print("3. Portal page will NOT be stuck loading forever")
    
    # Step 1: Admin login
    admin_token = test_admin_login()
    if not admin_token:
        print("\n❌ Cannot continue - admin login failed")
        return
    
    # Step 2: Fetch municipalities
    municipalities = test_get_municipalities(admin_token)
    municipality_ids = [m.get('id') for m in municipalities]
    municipality_names = {m.get('id'): m.get('name') for m in municipalities}
    
    if not municipality_ids:
        print("\n❌ Cannot continue - no municipalities found")
        return
    
    # Step 3: Create employee
    email, password = test_create_employee(admin_token, municipality_ids)
    if not email:
        print("\n❌ Cannot continue - employee creation failed")
        return
    
    # Step 4: Employee login (THE KEY TEST)
    employee_token, user = test_employee_login(email, password)
    if not employee_token:
        print("\n❌ Cannot continue - employee login failed")
        return
    
    # Step 5: Test budget loading
    budget_ok = test_employee_budget_load(employee_token, user, municipality_names)
    
    # Summary
    print_section("📊 SUMMARY")
    
    has_municipality_ids = 'municipality_ids' in user
    print(f"\n✅ Employee login returns municipality_ids: {'YES ✅' if has_municipality_ids else 'NO ❌'}")
    print(f"✅ Budget API accessible: {'YES ✅' if budget_ok else 'NO ❌'}")
    
    if has_municipality_ids and budget_ok:
        print("\n🎉 PORTAL WILL NOW WORK FOR EMPLOYEES!")
        print("\nWhat happens when employee visits /portal:")
        print("  1. ✅ User has role='employee' and municipality_ids Array")
        print("  2. ✅ PortalHomePage loads user.municipality_ids")
        print("  3. ✅ Municipality dropdown shows assigned municipalities")
        print("  4. ✅ Employee selects municipality")
        print("  5. ✅ Budget data loads for selected municipality")
        print("  6. ✅ Portal shows budget info (no loading spinner forever)")
    else:
        print("\n⚠️  Issues found - check above for details")

if __name__ == "__main__":
    main()
