```python
"""
Trigger staging crawler via API with specific URL targeting
Enhanced with improved detection logic and debugging capabilities
"""

import json
import urllib.request
import sys
from datetime import datetime

STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/crawl'

# Specific blog post URL that needs to be crawled
TARGET_BLOG_POST = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'

# Additional debugging endpoint to verify post detection
VERIFY_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/verify'

print("Triggering staging crawler with enhanced detection...")
print(f"API: {STAGING_API}")
print(f"Target URL: {TARGET_BLOG_POST}")
print(f"Target Post Date: March 2, 2026\n")

# Prepare payload with enhanced crawler options
# Include force_refresh to ensure the specific URL is re-crawled
# Added date_range filter to ensure posts from March 2026 are included
# Added validation_mode to check detection logic before crawling
payload = {
    'target_urls': [TARGET_BLOG_POST],
    'force_refresh': True,
    'crawl_depth': 1,
    'include_patterns': [
        '/blogs/desktop-and-application-streaming/*'
    ],
    # Enhanced detection settings to catch posts that may have been missed
    'detection_settings': {
        'date_range': {
            'start': '2026-03-01',
            'end': '2026-03-31'
        },
        'check_existing': True,
        'validate_metadata': True,
        'retry_failed': True
    },
    # Enable verbose logging for debugging detection issues
    'debug_mode': True,
    'log_level': 'DEBUG',
    # Explicitly include selectors for blog post metadata
    'metadata_selectors': {
        'title': ['h1.blog-post-title', 'h1[class*="title"]', 'article h1'],
        'date': ['time[datetime]', '.post-date', 'meta[property="article:published_time"]'],
        'content': ['article', '.post-content', 'main']
    }
}

def verify_post_exists(url):
    """
    Verify that the blog post URL is accessible and contains expected content
    This helps diagnose if the issue is with the URL itself or the crawler
    """
    try:
        print("Verifying target URL accessibility...")
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'AWS-Staging-Crawler-Verification/1.0'
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                content = response.read().decode('utf-8', errors='ignore')
                # Check for key indicators that this is a valid blog post
                indicators = [
                    'Amazon WorkSpaces',
                    'Graphics G6',
                    'Gr6',
                    'G6f',
                    'bundles'
                ]
                found = sum(1 for indicator in indicators if indicator in content)
                print(f"✓ URL is accessible (HTTP 200)")
                print(f"✓ Found {found}/{len(indicators)} expected content indicators")
                return True
            else:
                print(f"⚠ Unexpected status code: {response.status}")
                return False
    except Exception as e:
        print(f"⚠ URL verification failed: {e}")
        return False

# Verify the blog post exists before triggering crawler
print("=" * 60)
url_accessible = verify_post_exists(TARGET_BLOG_POST)
print("=" * 60 + "\n")

if not url_accessible:
    print("⚠ Warning: Target URL may not be accessible or may not contain expected content")
    print("Proceeding with crawl anyway to test detection logic...\n")

try:
    req = urllib.request.Request(
        STAGING_API,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'AWS-Staging-Crawler-Trigger/2.0',
            'X-Crawler-Version': '2.0',
            'X-Debug-Mode': 'true'
        },
        method='POST'
    )
    
    print("Sending crawl request...")
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode('utf-8'))
    
    print("✅ Crawler triggered successfully")
    print(f"\nRequest Payload:")
    print(json.dumps(payload, indent=2))
    print(f"\nResponse:")
    print(json.dumps(data, indent=2))
    
    # Enhanced response checking
    if 'crawl_id' in data or 'job_id' in data:
        crawl_id = data.get('crawl_id') or data.get('job_id')
        print("\n✓ Crawl job queued successfully")
        print(f"Crawl ID: {crawl_id}")
        print(f"Monitor at: staging.awseuccontent.com")
        
        # Check for any warnings or detection issues in the response
        if 'warnings' in data:
            print("\n⚠ Warnings:")
            for warning in data['warnings']:
                print(f"  - {warning}")
        
        if 'detection_info' in data:
            print("\n📊 Detection Information:")
            print(json.dumps(data['detection_info'], indent=2))
    else:
        print("\n⚠ Warning: Response does not contain expected job ID")
        print("The crawl may not have been queued properly")
    
    # Log timestamp for tracking
    print(f"\nCrawl triggered at: {datetime.now().isoformat()}")
    
except urllib.error.HTTPError as e:
    print(f"❌ HTTP ERROR {e.code}: {e.reason}")
    try:
        error_body = e.read().decode('utf-8')
        print(f"Error details: {error_body}")
        
        # Check for specific error codes that indicate detection issues
        if e.code == 404:
            print("\n💡 Possible cause: API endpoint may have changed")
        elif e.code == 400:
            print("\n💡 Possible cause: Payload format issue or invalid parameters")
        elif e.code == 422:
            print("\n💡 Possible cause: URL validation failed - post may not be detectable")
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

print("\n" + "=" * 60)
print("TROUBLESHOOTING TIPS:")
print("1. Check staging crawler logs for detection errors")
print("2. Verify date parsing logic handles 'March 2, 2026' format")
print("3. Ensure crawler's date filter includes posts from March 2026")
print("4. Check if robots.txt or rate limiting is blocking the crawler")
print("5. Verify metadata selectors match the blog post's HTML structure")
print("=" * 60)
```