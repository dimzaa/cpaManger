#!/usr/bin/env python3
"""Test the budget endpoint."""
import requests

# Get token
login_resp = requests.post('http://localhost:8000/api/auth/login', json={'email':'admin@example.com','password':'admin123'})
token = login_resp.json()['access_token']

# Get budget
headers = {'Authorization': f'Bearer {token}'}
resp = requests.get('http://localhost:8000/api/budget/4/2026-03', headers=headers)
print(f'Status: {resp.status_code}')
if resp.status_code == 200:
    data = resp.json()
    print(f'Got budget with {len(data.get("budget_lines", []))} lines')
else:
    print(f'Error: {resp.text[:200]}')
