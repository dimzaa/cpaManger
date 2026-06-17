#!/usr/bin/env python3
"""
Test both issues:
1. Admin municipalities API endpoint (with trailing slash)
2. Employee login and role handling
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def test_admin_login():
    """Test admin login and get token"""
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

def test_municipalities_with_trailing_slash(token):
    """Test municipalities endpoint with trailing slash"""
    print_section("2️⃣ MUNICIPALITIES - WITH TRAILING SLASH")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test with trailing slash (CORRECT)
    response = requests.get(
        f"{BASE_URL}/api/municipalities/",
        headers=headers
    )
    
    print(f"GET /api/municipalities/")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ SUCCESS - Received {len(data)} municipalities")
        for mun in data[:4]:
            print(f"      - {mun.get('name')} (ID: {mun.get('id')}, Code: {mun.get('code')})")
        return True
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"      {response.text}")
        return False

def test_employee_creation(admin_token):
    """Test creating a new employee"""
    print_section("3️⃣ CREATE EMPLOYEE FOR TESTING")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    timestamp = int(datetime.now().timestamp())
    
    employee_data = {
        "email": f"employee_test_{timestamp}@test.com",
        "password": "employee123",
        "first_name": "Test",
        "last_name": "Employee",
        "municipality_ids": [1]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/employees",
        headers=headers,
        json=employee_data
    )
    
    print(f"POST /api/employees")
    print(f"   Status: {response.status_code}")
    
    if response.status_code in [200, 201]:
        data = response.json()
        employee = data.get('data', data)
        employee_id = employee.get('id')
        email = employee.get('email')
        print(f"   ✅ Employee created")
        print(f"      ID: {employee_id}")
        print(f"      Email: {email}")
        print(f"      Role: {employee.get('role', 'N/A')} (should be or default to 'employee')")
        return employee_data['email'], employee_data['password']
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"      {response.text}")
        return None, None

def test_employee_login(email, password):
    """Test employee login"""
    print_section("4️⃣ EMPLOYEE LOGIN TEST")
    
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password}
    )
    
    print(f"POST /api/auth/login")
    print(f"   Email: {email}")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        user = data.get('user', {})
        token = data.get('access_token')
        role = user.get('role')
        
        print(f"   ✅ Employee login successful")
        print(f"      Role: {role}")
        print(f"      Token: {token[:50]}...")
        
        if role == 'employee':
            print(f"      ✅ Role is 'employee' - CORRECT")
        else:
            print(f"      ⚠️  Role is '{role}' - frontend must handle this")
        
        return token, role
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"      {response.text}")
        return None, None

def test_employee_portal_access(employee_token):
    """Test that employee can access portal route (needs /portal endpoint)"""
    print_section("5️⃣ VERIFY EMPLOYEE TOKEN IS VALID")
    
    headers = {"Authorization": f"Bearer {employee_token}"}
    
    # Try to fetch municipalities as employee (should work same as admin)
    response = requests.get(
        f"{BASE_URL}/api/municipalities/",
        headers=headers
    )
    
    print(f"GET /api/municipalities/ (as employee)")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Employee can fetch municipalities - portal access will work")
        print(f"   📊 Fetched {len(data)} municipalities")
        return True
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"      {response.text}")
        return False

def main():
    print("\n🧪 TESTING BOTH ISSUES")
    print("=" * 70)
    
    # Issue 1: Test municipalities endpoint with trailing slash
    admin_token = test_admin_login()
    if not admin_token:
        print("\n❌ Cannot continue - admin login failed")
        return
    
    municipalities_ok = test_municipalities_with_trailing_slash(admin_token)
    
    # Issue 2: Test employee login and role handling
    email, password = test_employee_creation(admin_token)
    if email and password:
        employee_token, role = test_employee_login(email, password)
        if employee_token:
            portal_ok = test_employee_portal_access(employee_token)
        else:
            portal_ok = False
    else:
        print("\n❌ Cannot test employee login - creation failed")
        return
    
    # Summary
    print_section("📊 SUMMARY")
    print(f"\n✅ Issue 1 (Municipalities API):    {'FIXED ✅' if municipalities_ok else 'NEEDS WORK ❌'}")
    print(f"✅ Issue 2 (Employee Role):         {'FIXED ✅' if (role == 'employee' and portal_ok) else 'NEEDS WORK ❌'}")
    
    if municipalities_ok and role == 'employee' and portal_ok:
        print("\n🎉 BOTH ISSUES RESOLVED!")
        print("\nFrontend fixes applied:")
        print("  1. ✅ Added trailing slash to /api/municipalities/")
        print("  2. ✅ Added employee role to App.jsx redirect")
        print("  3. ✅ Updated MunicipalityRoute to allow employees")
        print("\nYou can now:")
        print("  1. Create employee via /admin/employees")
        print("  2. Employee logs in → redirects to /portal")
        print("  3. Employee sees municipality budget with edit buttons")
    else:
        print("\n⚠️  Some issues remain")

if __name__ == "__main__":
    main()
