```python
"""
Trigger staging crawler via API with specific URL targeting
Enhanced with date filtering diagnostics and crawler validation
"""

import json
import urllib.request
import sys
from datetime import datetime, timezone

STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/crawl'

# Specific blog post URL that needs to be crawled
TARGET_BLOG_POST = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'

# Expected publication date of the blog post for validation
EXPECTED_POST_DATE = '2026-03-02'

print("Triggering staging crawler with enhanced diagnostics...")
print(f"API: {STAGING_API}")
print(f"Target URL: {TARGET_BLOG_POST}")
print(f"Expected Post Date: {EXPECTED_POST_DATE}")
print(f"Current Time (UTC): {datetime.now(timezone.utc).isoformat()}\n")

# Prepare payload with target URL and crawler options
# Enhanced payload to address potential date filtering and scraping issues
payload = {
    'target_urls': [TARGET_BLOG_POST],
    'force_refresh': True,  # Force re-crawl even if URL was previously visited
    'crawl_depth': 1,
    'include_patterns': [
        '/blogs/desktop-and-application-streaming/*',
        '/blogs/*/amazon-workspaces-*'  # Additional pattern for WorkSpaces posts
    ],
    # Enhanced date filtering configuration
    'date_filters': {
        'enabled': False,  # Disable date filtering to ensure post is captured
        'start_date': '2026-03-01',  # If enabled, would filter from this date
        'end_date': '2026-03-31',
        'ignore_missing_dates': True  # Don't skip posts without detectable dates
    },
    # URL detection configuration
    'url_detection': {
        'check_sitemap': True,  # Check sitemap for new URLs
        'check_rss': True,  # Check RSS feeds
        'follow_canonical': True,  # Follow canonical URLs
        'validate_links': True  # Validate that links are accessible
    },
    # Enhanced scraping patterns for better content extraction
    'scraping_config': {
        'extract_metadata': True,  # Extract all metadata including publish date
        'parse_json_ld': True,  # Parse JSON-LD structured data
        'extract_og_tags': True,  # Extract Open Graph tags
        'extract_article_schema': True,  # Extract article schema markup
        'selectors': {
            'title': ['h1.blog-post-title', 'h1', 'article h1', '.post-title'],
            'date': [
                'meta[property="article:published_time"]',
                'time[datetime]',
                '.post-date',
                '.published-date',
                'meta[name="publish-date"]'
            ],
            'content': ['article', '.post-content', '.blog-post-content', 'main'],
            'author': ['.author', '.post-author', 'meta[name="author"]']
        },
        'require_date': False  # Don't skip posts if date extraction fails
    },
    # Debugging and logging options
    'debug': {
        'verbose_logging': True,  # Enable detailed logging
        'save_raw_html': True,  # Save raw HTML for inspection
        'log_date_extraction': True,  # Log date extraction attempts
        'log_url_patterns': True,  # Log URL pattern matching
        'trace_filtering': True  # Trace why posts might be filtered out
    },
    # Retry configuration for robustness
    'retry_config': {
        'max_retries': 3,
        'retry_on_timeout': True,
        'retry_on_http_error': True,
        'backoff_multiplier': 2
    },
    # Additional metadata for tracking
    'metadata': {
        'trigger_reason': 'Missing blog post investigation',
        'post_topic': 'Amazon WorkSpaces Graphics G6 bundles',
        'expected_date': EXPECTED_POST_DATE,
        'investigation_date': datetime.now(timezone.utc).isoformat()
    }
}

print("Enhanced Crawler Configuration:")
print("=" * 60)
print("✓ Force refresh enabled - will re-crawl even if cached")
print("✓ Date filtering DISABLED - ensures post won't be filtered by date")
print("✓ Multiple URL patterns configured for better detection")
print("✓ Enhanced scraping selectors for metadata extraction")
print("✓ Verbose logging enabled for diagnostics")
print("✓ Date extraction validation without strict requirements")
print("=" * 60)
print()

try:
    req = urllib.request.Request(
        STAGING_API,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'AWS-Staging-Crawler-Trigger/2.0-Enhanced',
            'X-Crawler-Debug': 'true',  # Signal API to enable debug mode
            'X-Investigation': 'missing-post-2026-03-02'  # Tag for tracking
        },
        method='POST'
    )
    
    with urllib.request.urlopen(req, timeout=60) as response:  # Increased timeout for verbose mode
        data = json.loads(response.read().decode('utf-8'))
    
    print("✅ Crawler triggered successfully")
    print(f"\nRequest Payload (abbreviated):")
    # Print abbreviated payload for readability
    print(json.dumps({
        'target_urls': payload['target_urls'],
        'force_refresh': payload['force_refresh'],
        'date_filters_enabled': payload['date_filters']['enabled'],
        'debug_enabled': payload['debug']['verbose_logging'],
        'metadata': payload['metadata']
    }, indent=2))
    
    print(f"\nResponse:")
    print(json.dumps(data, indent=2))
    
    # Enhanced response validation
    if 'crawl_id' in data or 'job_id' in data:
        job_id = data.get('crawl_id') or data.get('job_id')
        print("\n✓ Crawl job queued successfully")
        print(f"Job ID: {job_id}")
        print(f"Monitor at: staging.awseuccontent.com")
        
        # Provide diagnostic recommendations
        print("\n" + "=" * 60)
        print("DIAGNOSTIC RECOMMENDATIONS:")
        print("=" * 60)
        print("1. Check crawler logs for date extraction attempts")
        print("2. Verify URL pattern matching in verbose logs")
        print("3. Review saved raw HTML if post structure has changed")
        print("4. Confirm post is published and publicly accessible")
        print("5. Check if robots.txt or meta tags are blocking crawler")
        print(f"6. Verify expected date ({EXPECTED_POST_DATE}) in post metadata")
        print("=" * 60)
        
    else:
        print("\n⚠ Warning: Response doesn't contain expected job ID")
        print("The request may not have been queued properly")
    
except urllib.error.HTTPError as e:
    print(f"❌ HTTP ERROR {e.code}: {e.reason}")
    try:
        error_body = e.read().decode('utf-8')
        print(f"Error details: {error_body}")
    except:
        pass
    print("\nTroubleshooting tips:")
    print("- Verify API endpoint is correct and accessible")
    print("- Check if API authentication/authorization is required")
    print("- Validate target URL is accessible")
    sys.exit(1)
    
except urllib.error.URLError as e:
    print(f"❌ URL ERROR: {e.reason}")
    print("Check network connectivity and API endpoint availability")
    print("\nTroubleshooting tips:")
    print("- Verify internet connection")
    print("- Check if API endpoint URL is correct")
    print("- Confirm no firewall/proxy blocking the request")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    print("\nAn unexpected error occurred. Review the traceback above.")
    sys.exit(1)
```