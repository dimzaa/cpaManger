import requests

# Login
resp = requests.post('http://127.0.0.1:8000/api/auth/login',
    json={'email': 'admin@example.com', 'password': 'admin123'},
    timeout=10)

print('Login Status:', resp.status_code)

if resp.status_code == 200:
    token = resp.json()['access_token']
    print('Token obtained')
    
    # Test budget endpoint
    headers = {'Authorization': f'Bearer {token}'}
    resp = requests.get('http://127.0.0.1:8000/api/budget/4/2026-03', headers=headers, timeout=10)
    
    print('Budget API Status:', resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        print('SUCCESS - Got budget data')
        print('  Invoice total:', data.get('invoice_total'))
        print('  Budget lines:', len(data.get('budget_lines', [])))
    else:
        print('ERROR:', resp.text[:100])
