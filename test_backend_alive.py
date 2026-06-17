"""
Simple test to see if upload endpoint processes files
"""
import requests
import sys

BACKEND_URL = "http://localhost:8000"

# Test if backend is responding
try:
    response = requests.get(f"{BACKEND_URL}/api/municipalities", timeout=5)
    if response.status_code == 401:
        print("✅ Backend is running and responding")
    else:
        print(f"⚠️  Backend response: {response.status_code}")
except Exception as e:
    print(f"❌ Backend not responding: {e}")
    sys.exit(1)
