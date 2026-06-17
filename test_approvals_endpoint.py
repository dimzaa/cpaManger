#!/usr/bin/env python3
"""Test the CPA approvals endpoint."""
import requests

# Get token
login_resp = requests.post('http://localhost:8000/api/auth/login', json={'email':'admin@example.com','password':'admin123'})
token = login_resp.json()['access_token']

# Get approvals
headers = {'Authorization': f'Bearer {token}'}
resp = requests.get('http://localhost:8000/api/suggestions/pending', headers=headers)
print(f'Status: {resp.status_code}')
if resp.status_code == 200:
    data = resp.json()
    print(f'Got {len(data)} pending suggestions')
    for sug in data:
        print(f'  - ID {sug["id"]}: {sug["suggestion_type"]} from {sug["suggester_name"]}')
else:
    print(f'Error: {resp.text[:200]}')
