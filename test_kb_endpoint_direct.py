#!/usr/bin/env python3
"""
Test KB documents endpoint directly
"""

import requests
import json

# Get JWT token from user
print("=" * 70)
print("Test KB Documents Endpoint - Staging")
print("=" * 70)
print()
print("To get your JWT token:")
print("1. Go to https://staging.awseuccontent.com")
print("2. Sign in")
print("3. Open DevTools (F12)")
print("4. Go to Application > Local Storage > https://staging.awseuccontent.com")
print("5. Copy the value of 'id_token'")
print()

token = input("Paste your JWT token: ").strip()

if not token:
    print("❌ No token provided")
    exit(1)

# Test the endpoint
url = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/kb-documents'
headers = {
    'Authorization': f'Bearer {token}'
}

print(f"\n📤 Testing: GET {url}")
print(f"   Authorization: Bearer {token[:20]}...")

try:
    response = requests.get(url, headers=headers)
    
    print(f"\n📥 Response:")
    print(f"   Status: {response.status_code}")
    print(f"   Headers:")
    for key, value in response.headers.items():
        if 'access-control' in key.lower() or 'content-type' in key.lower():
            print(f"     {key}: {value}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Success!")
        print(f"   Documents: {len(data.get('documents', []))}")
        for doc in data.get('documents', []):
            print(f"     - {doc['name']}")
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(f"   Body: {response.text[:500]}")

except Exception as e:
    print(f"\n❌ Exception: {str(e)}")
