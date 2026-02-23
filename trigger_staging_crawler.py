"""
Trigger staging crawler via API
"""

import json
import urllib.request

STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/crawl'

print("Triggering staging crawler...")
print(f"API: {STAGING_API}\n")

try:
    req = urllib.request.Request(
        STAGING_API,
        data=b'{}',
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode('utf-8'))
    
    print("✅ Crawler triggered successfully")
    print(f"\nResponse:")
    print(json.dumps(data, indent=2))
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
