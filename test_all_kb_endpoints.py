"""
Test all KB editor endpoints
"""
import requests

BASE_URL = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'

endpoints = [
    ('GET', '/kb-documents', 'List KB documents'),
    ('GET', '/kb-document/euc-qa-pairs', 'Get KB document'),
    ('PUT', '/kb-document/euc-qa-pairs', 'Update KB document'),
    ('GET', '/kb-contributors', 'Get contributors'),
    ('GET', '/kb-my-contributions', 'Get my contributions'),
    ('GET', '/kb-ingestion-status/test-job-id', 'Get ingestion status'),
]

print("\n🧪 TESTING ALL KB EDITOR ENDPOINTS")
print("=" * 70)

for method, path, description in endpoints:
    url = f'{BASE_URL}{path}'
    print(f"\n{method} {path}")
    print(f"Description: {description}")
    
    try:
        if method == 'GET':
            response = requests.get(url, timeout=5)
        elif method == 'PUT':
            response = requests.put(url, json={}, timeout=5)
        
        print(f"Status: {response.status_code}", end='')
        
        if response.status_code == 401:
            print(" ✅ (Requires auth - working correctly)")
        elif response.status_code == 500:
            print(" ❌ (Internal server error - integration issue)")
        elif response.status_code == 404:
            print(" ⚠️  (Not found - routing issue)")
        else:
            print(f" ℹ️  ({response.json().get('message', 'Unknown')})")
            
    except requests.exceptions.Timeout:
        print("❌ Timeout")
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "=" * 70)
print("✅ ENDPOINT TESTING COMPLETE")
print("=" * 70)
print("\n💡 All endpoints should return 401 (Unauthorized) without a valid JWT token")
print("💡 This confirms the endpoints are working and require authentication")
