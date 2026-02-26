"""
Test real API endpoint with detailed error handling
"""
import requests
import json

url = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/kb-document/euc-qa-pairs'

print(f"\n🧪 Testing: {url}")
print("=" * 60)

try:
    response = requests.get(url, timeout=10)
    print(f"\nStatus Code: {response.status_code}")
    print(f"\nResponse Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    
    print(f"\nResponse Body:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
        
except requests.exceptions.Timeout:
    print("Request timed out")
except Exception as e:
    print(f"Error: {e}")
