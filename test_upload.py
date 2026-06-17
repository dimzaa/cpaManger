"""
Test script to upload and test the Ministry budget ZIP file.

Usage:
    python test_upload.py
"""

import requests
import json
from pathlib import Path

# Configuration
BACKEND_URL = "http://localhost:8000"
UPLOAD_ENDPOINT = f"{BACKEND_URL}/api/upload"
LOGIN_ENDPOINT = f"{BACKEND_URL}/api/auth/login"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

# File to upload (the most recent Horada.zip)
ZIP_FILE = "uploads/20260402_163222_Horada.zip"

def get_auth_token():
    """Get authentication token for admin user."""
    print("🔐 Authenticating admin user...")
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
    
    data = response.json()
    token = data.get("access_token")
    print(f"✅ Got auth token")
    return token

def test_upload():
    """Test the upload endpoint with Ministry budget file."""
    
    # Check if file exists
    if not Path(ZIP_FILE).exists():
        print(f"❌ File not found: {ZIP_FILE}")
        return False
    
    print(f"\n📦 Testing upload with: {ZIP_FILE}")
    print(f"   File size: {Path(ZIP_FILE).stat().st_size:,} bytes")
    
    # Get auth token
    token = get_auth_token()
    if not token:
        return False
    
    # Prepare upload
    print(f"\n📤 Uploading file...")
    headers = {"Authorization": f"Bearer {token}"}
    
    with open(ZIP_FILE, 'rb') as f:
        files = {
            'file': (Path(ZIP_FILE).name, f, 'application/zip')
        }
        data = {
            'month': '3',
            'year': '2026'
        }
        
        response = requests.post(
            UPLOAD_ENDPOINT,
            headers=headers,
            files=files,
            data=data
        )
    
    print(f"\nResponse status: {response.status_code}")
    
    if response.status_code == 200:
        print(f"✅ Upload successful!")
        result = response.json()
        print(f"\n📊 Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return True
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"\n📝 Response:")
        try:
            error = response.json()
            print(json.dumps(error, indent=2, ensure_ascii=False))
        except:
            print(response.text)
        return False

if __name__ == '__main__':
    print("=" * 70)
    print("🧪 Testing Ministry Budget Upload")
    print("=" * 70)
    
    success = test_upload()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ Test passed!")
    else:
        print("❌ Test failed!")
    print("=" * 70)
