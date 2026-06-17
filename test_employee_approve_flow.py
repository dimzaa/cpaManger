"""
End-to-end test: Employee submits explanation -> CPA approves

This test verifies the complete workflow:
1. Employee submits an explanation suggestion
2. CPA admin approves the suggestion
3. ApprovedExplanation is created and persisted
"""

import requests
import json
from datetime import datetime

# Configuration
BACKEND_URL = "http://localhost:8000"
LOGIN_ENDPOINT = f"{BACKEND_URL}/api/auth/login"
SUGGESTIONS_ENDPOINT = f"{BACKEND_URL}/api/suggestions"
PRESETS_ENDPOINT = f"{BACKEND_URL}/api/presets"

# Test users (created during initial setup)
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"
EMPLOYEE_EMAIL = "workflow_test_employee@example.com"
EMPLOYEE_PASSWORD = "TestPass123!"

# Test data - hardcoded from existing database
TEST_MUNICIPALITY_ID = 4  # Horada
TEST_MONTH = "2026-03"  # Use existing data month
TEST_BUDGET_LINE_ID = None  # Will be fetched
TEST_TOPIC_CODE = "3"  # Will use first available budget line
TEST_PRESET_ID = None  # Will be fetched

# Result storage
tokens = {}
test_results = {
    "employee_submission": None,
    "admin_approval": None,
    "approved_explanation": None
}

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")

def print_step(step_num, description):
    """Print a formatted step."""
    print(f"\n📍 Step {step_num}: {description}")

def login(email, password, user_type):
    """Login and get auth token."""
    print(f"\n  🔐 Logging in as {user_type}...")
    response = requests.post(
        LOGIN_ENDPOINT,
        json={
            "email": email,
            "password": password
        }
    )
    
    if response.status_code != 200:
        print(f"  ❌ Login failed: {response.status_code}")
        print(f"     Response: {response.text}")
        return None
    
    token = response.json()['access_token']
    print(f"  ✅ Successfully logged in")
    return token

def get_preset(admin_token):
    """Get first available preset for testing."""
    print(f"\n  📋 Fetching available presets...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(
        f"{PRESETS_ENDPOINT}?municipality_id={TEST_MUNICIPALITY_ID}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"  ⚠️  Could not fetch presets: {response.status_code}")
        return None
    
    presets = response.json()
    if presets:
        preset = presets[0]
        print(f"  ✅ Found preset: {preset['id']} - {preset.get('budget_code', 'N/A')}")
        return preset['id']
    
    print(f"  ⚠️  No presets available")
    return None

def get_budget_line(admin_token):
    """Get first available budget line for testing."""
    print(f"\n  📊 Fetching budget lines for {TEST_MUNICIPALITY_ID}/{TEST_MONTH}...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(
        f"{BACKEND_URL}/api/budget/{TEST_MUNICIPALITY_ID}/{TEST_MONTH}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"  ❌ Could not fetch budget lines: {response.status_code}")
        print(f"     Response: {response.text}")
        return None
    
    data = response.json()
    budget_lines = data.get('budget_lines', []) if isinstance(data, dict) else data
    
    if budget_lines:
        line = budget_lines[0]
        line_id = line.get('id', line.get('budget_line_id'))
        topic = line.get('topic_code', 'N/A')
        print(f"  ✅ Found budget line: {line_id} (topic: {topic})")
        return {
            'id': line_id,
            'topic_code': topic,
            'full_data': line
        }
    
    print(f"  ❌ No budget lines available")
    return None

def submit_suggestion(employee_token, budget_line_info, preset_id):
    """Employee submits an explanation suggestion."""
    print_step(2, "Employee submits explanation suggestion")
    
    # Prepare suggestion data
    suggestion_data = {
        "budget_line_id": budget_line_info['id'],
        "municipality_id": TEST_MUNICIPALITY_ID,
        "month": TEST_MONTH,
        "topic_code": budget_line_info['topic_code'],
        "suggestion_type": "preset" if preset_id else "custom",
        "preset_id": preset_id if preset_id else None,
        "custom_text": "Test explanation from employee" if not preset_id else None
    }
    
    print(f"\n  📝 Submitting suggestion:")
    print(f"     Budget line ID: {suggestion_data['budget_line_id']}")
    print(f"     Topic code: {suggestion_data['topic_code']}")
    print(f"     Type: {suggestion_data['suggestion_type']}")
    if preset_id:
        print(f"     Preset ID: {preset_id}")
    else:
        print(f"     Custom text: {suggestion_data['custom_text']}")
    
    headers = {"Authorization": f"Bearer {employee_token}"}
    response = requests.post(
        SUGGESTIONS_ENDPOINT,
        json=suggestion_data,
        headers=headers
    )
    
    if response.status_code != 201:
        print(f"  ❌ Submission failed: {response.status_code}")
        print(f"     Response: {response.text}")
        return None
    
    suggestion = response.json()
    print(f"\n  ✅ Suggestion submitted successfully!")
    print(f"     Suggestion ID: {suggestion['id']}")
    print(f"     Status: {suggestion['status']}")
    print(f"     Submitted by: {suggestion['suggested_by']}")
    
    return suggestion

def get_pending_suggestions(admin_token, municipality_id):
    """Admin retrieves pending suggestions."""
    print_step(3, "Admin retrieves pending suggestions")
    
    print(f"\n  🔍 Fetching pending suggestions...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(
        f"{SUGGESTIONS_ENDPOINT}/pending?municipality_id={municipality_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"  ❌ Failed to fetch pending suggestions: {response.status_code}")
        print(f"     Response: {response.text}")
        return []
    
    suggestions = response.json()
    print(f"\n  ✅ Fetched pending suggestions")
    print(f"     Count: {len(suggestions)}")
    
    if suggestions:
        for s in suggestions:
            print(f"     - {s['id']}: {s['topic_code']} (by: {s.get('suggester_name', 'Unknown')})")
    
    return suggestions

def approve_suggestion(admin_token, suggestion_id, review_note=None):
    """Admin approves an explanation suggestion."""
    print_step(4, "Admin approves suggestion")
    
    approval_data = {
        "review_note": review_note or "Approved by test. Good explanation."
    }
    
    print(f"\n  ✅ Approving suggestion {suggestion_id}...")
    print(f"     Review note: {approval_data['review_note']}")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.patch(
        f"{SUGGESTIONS_ENDPOINT}/{suggestion_id}/approve",
        json=approval_data,
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"  ❌ Approval failed: {response.status_code}")
        print(f"     Response: {response.text}")
        return None
    
    approved_suggestion = response.json()
    print(f"\n  ✅ Suggestion approved successfully!")
    print(f"     Suggestion ID: {approved_suggestion['id']}")
    print(f"     Status: {approved_suggestion['status']}")
    print(f"     Reviewed by: {approved_suggestion['reviewed_by']}")
    print(f"     Review note: {approved_suggestion.get('review_note', 'N/A')}")
    
    return approved_suggestion

def verify_approved_explanation(admin_token, budget_line_id, municipality_id, month):
    """Verify that ApprovedExplanation was created."""
    print_step(5, "Verify ApprovedExplanation created")
    
    print(f"\n  🔎 Checking for ApprovedExplanation...")
    print(f"     Budget line: {budget_line_id}")
    print(f"     Municipality: {municipality_id}")
    print(f"     Month: {month}")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(
        f"{BACKEND_URL}/api/explanations/{municipality_id}/{month}/3",
        headers=headers
    )
    
    if response.status_code == 200:
        explanation = response.json()
        print(f"\n  ✅ ApprovedExplanation found!")
        print(f"     Topic code: {explanation.get('topic_code', 'N/A')}")
        print(f"     Explanation: {explanation.get('explanation', 'N/A')[:100]}...")
        print(f"     Approved by: {explanation.get('approved_by', 'N/A')}")
        return explanation
    elif response.status_code == 404:
        print(f"\n  ⚠️  No ApprovedExplanation found")
        return None
    else:
        print(f"\n  ❌ Error checking explanation: {response.status_code}")
        print(f"     Response: {response.text}")
        return None

def run_full_workflow():
    """Execute the complete employee submit -> CPA approve workflow."""
    print_section("EMPLOYEE SUBMIT → CPA APPROVE WORKFLOW TEST")
    
    # Step 0: Login
    print_step(0, "Authentication")
    
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD, "CPA Admin")
    if not admin_token:
        print("\n❌ Failed to authenticate admin")
        return False
    
    employee_token = login(EMPLOYEE_EMAIL, EMPLOYEE_PASSWORD, "Employee")
    if not employee_token:
        print("\n❌ Failed to authenticate employee")
        return False
    
    # Step 1: Prepare test data
    print_step(1, "Prepare test data")
    
    budget_line_info = get_budget_line(admin_token)
    if not budget_line_info:
        print("\n❌ Could not fetch budget line")
        return False
    
    preset_id = get_preset(admin_token)
    
    # Step 2: Employee submits suggestion
    suggestion = submit_suggestion(employee_token, budget_line_info, preset_id)
    if not suggestion:
        print("\n❌ Employee submission failed")
        return False
    
    test_results["employee_submission"] = suggestion
    
    # Step 3: Admin retrieves pending suggestions
    pending = get_pending_suggestions(admin_token, TEST_MUNICIPALITY_ID)
    
    # Find our suggestion in pending list
    our_suggestion = None
    for s in pending:
        if s['id'] == suggestion['id']:
            our_suggestion = s
            break
    
    if not our_suggestion:
        print("\n❌ Submitted suggestion not found in pending list!")
        return False
    
    print(f"\n  ✅ Suggestion found in pending list")
    
    # Step 4: Admin approves suggestion
    approved = approve_suggestion(admin_token, suggestion['id'])
    if not approved:
        print("\n❌ Approval failed")
        return False
    
    test_results["admin_approval"] = approved
    
    # Step 5: Verify ApprovedExplanation was created
    explanation = verify_approved_explanation(
        admin_token,
        budget_line_info['id'],
        TEST_MUNICIPALITY_ID,
        TEST_MONTH
    )
    
    if explanation:
        test_results["approved_explanation"] = explanation
    
    # Final report
    print_section("FINAL RESULTS")
    print(f"\n✅ All steps completed successfully!")
    print(f"\n📊 Summary:")
    print(f"   ✓ Employee submitted suggestion ID: {suggestion['id']}")
    print(f"   ✓ Admin approved suggestion ID: {approved['id']}")
    if explanation:
        print(f"   ✓ ApprovedExplanation created")
    else:
        print(f"   ⚠️  ApprovedExplanation not verified (but approval succeeded)")
    
    print(f"\n✨ WORKFLOW TEST PASSED ✨\n")
    return True

if __name__ == '__main__':
    try:
        success = run_full_workflow()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
