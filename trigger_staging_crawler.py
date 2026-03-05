```python
"""
Trigger staging crawler via API with specific URL targeting
"""

import json
import urllib.request
import sys
from datetime import datetime

STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/crawl'

# Specific blog post URL that needs to be crawled
TARGET_BLOG_POST = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'

print("Triggering staging crawler...")
print(f"API: {STAGING_API}")
print(f"Target URL: {TARGET_BLOG_POST}")
print(f"Timestamp: {datetime.utcnow().isoformat()}Z\n")

# Prepare payload with target URL and crawler options
# Include force_refresh to ensure the specific URL is re-crawled
# Added debug mode to investigate detection issues
# Added date_filter to ensure content from March 2026 is included
payload = {
    'target_urls': [TARGET_BLOG_POST],
    'force_refresh': True,
    'crawl_depth': 1,
    'include_patterns': [
        '/blogs/desktop-and-application-streaming/*'
    ],
    'date_range': {
        'start': '2026-03-01',
        'end': '2026-03-31'
    },
    'debug_mode': True,
    'follow_redirects': True,
    'ignore_robots_txt': False,
    'user_agent': 'AWS-Staging-Crawler/2.0 (compatible; +https://staging.awseuccontent.com/bot)',
    'timeout': 60,
    'verify_ssl': True,
    'extract_metadata': True,
    'parse_publish_date': True
}

# Additional diagnostic request to verify blog post accessibility
print("Running pre-flight check on target URL...")
try:
    check_req = urllib.request.Request(
        TARGET_BLOG_POST,
        headers={
            'User-Agent': 'AWS-Staging-Crawler/2.0 (compatible; +https://staging.awseuccontent.com/bot)'
        }
    )
    with urllib.request.urlopen(check_req, timeout=10) as check_response:
        status_code = check_response.status
        content_type = check_response.headers.get('Content-Type', 'unknown')
        content_length = check_response.headers.get('Content-Length', 'unknown')
        last_modified = check_response.headers.get('Last-Modified', 'unknown')
        
        print(f"✓ Target URL is accessible")
        print(f"  Status: {status_code}")
        print(f"  Content-Type: {content_type}")
        print(f"  Content-Length: {content_length}")
        print(f"  Last-Modified: {last_modified}\n")
        
except Exception as e:
    print(f"⚠ Warning: Could not verify target URL accessibility: {e}")
    print("Proceeding with crawler trigger anyway...\n")

try:
    req = urllib.request.Request(
        STAGING_API,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'AWS-Staging-Crawler-Trigger/2.0',
            'X-Crawler-Priority': 'high',
            'X-Debug-Mode': 'true'
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
        crawl_id = data.get('crawl_id') or data.get('job_id')
        print("\n✓ Crawl job queued successfully")
        print(f"Crawl ID: {crawl_id}")
        print(f"Monitor at: https://staging.awseuccontent.com")
        print(f"Direct job status: https://staging.awseuccontent.com/jobs/{crawl_id}")
    
    # Display any warnings or detection issues from the response
    if 'warnings' in data:
        print("\n⚠ Warnings:")
        for warning in data['warnings']:
            print(f"  - {warning}")
    
    if 'debug_info' in data:
        print("\n🔍 Debug Information:")
        print(json.dumps(data['debug_info'], indent=2))
    
    # Provide troubleshooting guidance
    print("\n" + "="*60)
    print("TROUBLESHOOTING NOTES:")
    print("="*60)
    print("If the blog post is still not detected, check:")
    print("1. Blog post publication date metadata (should be 2026-03-02)")
    print("2. Staging crawler date filters and configuration")
    print("3. Blog post robots meta tags or noindex directives")
    print("4. Staging database for any existing entries with wrong dates")
    print("5. Crawler logs at staging.awseuccontent.com/logs")
    print("6. RSS feed inclusion: aws.amazon.com/blogs/.../feed/")
    print("="*60)
    
except urllib.error.HTTPError as e:
    print(f"❌ HTTP ERROR {e.code}: {e.reason}")
    try:
        error_body = e.read().decode('utf-8')
        print(f"Error details: {error_body}")
        
        # Try to parse error response for more details
        try:
            error_data = json.loads(error_body)
            if 'message' in error_data:
                print(f"Error message: {error_data['message']}")
            if 'details' in error_data:
                print(f"Error details: {json.dumps(error_data['details'], indent=2)}")
        except:
            pass
    except:
        pass
    sys.exit(1)
    
except urllib.error.URLError as e:
    print(f"❌ URL ERROR: {e.reason}")
    print("Check network connectivity and API endpoint availability")
    print(f"API endpoint: {STAGING_API}")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```