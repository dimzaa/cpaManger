"""
Create a test employee account and prepare test data for the workflow test
"""

import requests
import json
from datetime import datetime

BACKEND_URL = "http://localhost:8000"
LOGIN_ENDPOINT = f"{BACKEND_URL}/api/auth/login"
EMPLOYEES_ENDPOINT = f"{BACKEND_URL}/api/employees"

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

# Test employee credentials
TEST_EMPLOYEE_EMAIL = "workflow_test_employee@example.com"
TEST_EMPLOYEE_PASSWORD = "TestPass123!"

# Test municipality (from existing data)
TEST_MUNICIPALITY_ID = 4

def get_admin_token():
    """Get admin auth token."""
    print("🔐 Authenticating as admin...")
    response = requests.post(
        LOGIN_ENDPOINT,
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None
    
    token = response.json()['access_token']
    print(f"✅ Got admin token")
    return token

def create_employee(admin_token, email, password, municipality_id):
    """Create a new employee account."""
    print(f"\n👤 Creating employee account: {email}")
    
    employee_data = {
        "email": email,
        "password": password,
        "first_name": "Test",
        "last_name": "Employee",
        "municipality_ids": [municipality_id]
    }
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.post(
        EMPLOYEES_ENDPOINT,
        json=employee_data,
        headers=headers
    )
    
    if response.status_code == 201:
        employee = response.json()
        print(f"✅ Employee created successfully!")
        print(f"   Employee ID: {employee.get('id')}")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Assigned to municipality: {municipality_id}")
        return employee
    elif response.status_code == 409:
        print(f"⚠️  Employee already exists: {email}")
        # Try to login to verify credentials work
        print(f"\n   Testing login with: {email}")
        login_response = requests.post(
            LOGIN_ENDPOINT,
            json={"email": email, "password": password}
        )
        if login_response.status_code == 200:
            print(f"   ✅ Login successful with this password")
            return {"email": email, "password": password}
        else:
            print(f"   ⚠️  Login failed - employee exists but password may differ")
            return None
    else:
        print(f"❌ Failed to create employee: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def test_employee_login(email, password):
    """Test employee login."""
    print(f"\n🔐 Testing employee login: {email}")
    response = requests.post(
        LOGIN_ENDPOINT,
        json={"email": email, "password": password}
    )
    
    if response.status_code == 200:
        print(f"✅ Login successful!")
        return response.json()['access_token']
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

if __name__ == '__main__':
    print("=" * 70)
    print("CREATE TEST EMPLOYEE ACCOUNT")
    print("=" * 70)
    
    # Get admin token
    admin_token = get_admin_token()
    if not admin_token:
        print("\n❌ Failed to authenticate admin")
        exit(1)
    
    # Create employee
    employee = create_employee(admin_token, TEST_EMPLOYEE_EMAIL, TEST_EMPLOYEE_PASSWORD, TEST_MUNICIPALITY_ID)
    if not employee:
        print("\n❌ Failed to create employee")
        exit(1)
    
    # Test login
    employee_token = test_employee_login(TEST_EMPLOYEE_EMAIL, TEST_EMPLOYEE_PASSWORD)
    if not employee_token:
        print("\n❌ Failed to login as employee")
        exit(1)
    
    print("\n" + "=" * 70)
    print("✨ TEST EMPLOYEE ACCOUNT READY")
    print("=" * 70)
    print(f"\nUse these credentials for testing:")
    print(f"  Email: {TEST_EMPLOYEE_EMAIL}")
    print(f"  Password: {TEST_EMPLOYEE_PASSWORD}")
    print(f"  Municipality: {TEST_MUNICIPALITY_ID}")
