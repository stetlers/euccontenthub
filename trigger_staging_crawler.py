```python
"""
Trigger staging crawler via API with specific URL targeting
"""

import json
import urllib.request
import sys

STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/crawl'

# Specific blog post URL that needs to be crawled
TARGET_BLOG_POST = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'

print("Triggering staging crawler...")
print(f"API: {STAGING_API}")
print(f"Target URL: {TARGET_BLOG_POST}\n")

# Prepare payload with target URL and crawler options
# Include force_refresh to ensure the specific URL is re-crawled
payload = {
    'target_urls': [TARGET_BLOG_POST],
    'force_refresh': True,
    'crawl_depth': 1,
    'include_patterns': [
        '/blogs/desktop-and-application-streaming/*'
    ]
}

try:
    req = urllib.request.Request(
        STAGING_API,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'AWS-Staging-Crawler-Trigger/1.0'
        },
        method='POST'
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode('utf-8'))
    
    print("✅ Crawler triggered successfully")
    print(f"\nRequest Payload:")
    print(json.dumps(payload, indent=2))
    print(f"\nResponse:")
    print(json.dumps(data, indent=2))
    
    # Check if the response indicates successful queuing
    if 'crawl_id' in data or 'job_id' in data:
        print("\n✓ Crawl job queued successfully")
        print(f"Monitor at: staging.awseuccontent.com")
    
except urllib.error.HTTPError as e:
    print(f"❌ HTTP ERROR {e.code}: {e.reason}")
    try:
        error_body = e.read().decode('utf-8')
        print(f"Error details: {error_body}")
    except:
        pass
    sys.exit(1)
    
except urllib.error.URLError as e:
    print(f"❌ URL ERROR: {e.reason}")
    print("Check network connectivity and API endpoint availability")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```