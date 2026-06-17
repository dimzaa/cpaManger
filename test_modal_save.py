"""
Test the explanation edit modal save functionality
Simulate what the frontend modal does when save button is clicked
"""

import requests
import json
import time

BACKEND_URL = "http://localhost:8000"
LOGIN_ENDPOINT = f"{BACKEND_URL}/api/auth/login"
EXPLANATIONS_ENDPOINT = f"{BACKEND_URL}/api/explanations"

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

TEST_MUNICIPALITY_ID = 4
TEST_MONTH = "2026-03"
TEST_TOPIC_CODE = "0"

def test_modal_save():
    """Test the complete save button workflow."""
    print("="*70)
    print("TEST: ExplanationEditModal Save Button Functionality")
    print("="*70)
    
    # Step 1: Login
    print("\n📍 Step 1: Login as CPA Admin")
    response = requests.post(
        LOGIN_ENDPOINT,
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    token = response.json()['access_token']
    print(f"✅ Got token: {token[:30]}...")
    
    # Step 2: Simulate modal save - POST to explanations endpoint
    print(f"\n📍 Step 2: Simulate Save Button Click (handleSave)")
    print(f"   This is what happens when user clicks '💾 שמור' in the modal")
    
    # The modal calls: explanationsAPI.saveExplanation(municipalityId, month, topicCode, customText)
    # Which sends: POST /api/explanations/{municipalityId}/{month}/{topicCode}
    #              { "custom_text": "..." }
    
    new_explanation = f"הסבר נשמר דרך המודל - {time.strftime('%H:%M:%S')}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{EXPLANATIONS_ENDPOINT}/{TEST_MUNICIPALITY_ID}/{TEST_MONTH}/{TEST_TOPIC_CODE}"
    payload = {
        "custom_text": new_explanation
    }
    
    print(f"\n   📤 API Request Details:")
    print(f"      Method: POST")
    print(f"      URL: {url}")
    print(f"      Body: {json.dumps(payload, ensure_ascii=False)}")
    print(f"      Auth: Bearer {token[:20]}...")
    print(f"      Content-Type: application/json")
    
    response = requests.post(url, json=payload, headers=headers)
    
    print(f"\n   📥 API Response:")
    print(f"      Status Code: {response.status_code}")
    print(f"      Headers: {dict(response.headers)}")
    
    if response.status_code == 201:
        result = response.json()
        print(f"\n✅ Save successful!")
        print(f"   Response data:")
        print(f"      {json.dumps(result, ensure_ascii=False, indent=6)}")
        
        # Step 3: Verify the explanation was saved
        print(f"\n📍 Step 3: Verify saved explanation (simulating page refresh)")
        
        response = requests.get(
            f"{EXPLANATIONS_ENDPOINT}/municipality/{TEST_MUNICIPALITY_ID}/month/{TEST_MONTH}",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            explanations = data.get('explanations', [])
            
            our_explanation = None
            for exp in explanations:
                if exp.get('topic_code') == TEST_TOPIC_CODE:
                    our_explanation = exp
                    break
            
            if our_explanation and new_explanation in our_explanation.get('explanation', ''):
                print(f"✅ Explanation verified in database!")
                print(f"   Topic: {our_explanation.get('topic_code')}")
                print(f"   Text: {our_explanation.get('explanation')[:60]}...")
                print(f"   Is Custom: {our_explanation.get('is_custom')}")
                return True
            else:
                print(f"❌ Explanation not found or text doesn't match")
                return False
        else:
            print(f"❌ Failed to fetch explanations: {response.status_code}")
            return False
    else:
        print(f"\n❌ Save failed: {response.status_code}")
        print(f"   Response: {response.text}")
        
        # Try to extract error details
        try:
            error_data = response.json()
            print(f"   Error detail: {error_data}")
        except:
            pass
        
        return False

if __name__ == '__main__':
    try:
        success = test_modal_save()
        
        print(f"\n{'='*70}")
        if success:
            print("✨ MODAL SAVE BUTTON WORKS CORRECTLY ✨")
        else:
            print("❌ MODAL SAVE BUTTON HAS ISSUES")
        print(f"{'='*70}")
        
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
