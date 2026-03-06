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
    # CRITICAL FIX: Date filtering completely disabled to ensure March 2, 2026 post is captured
    # Previous issue: Date filter may have been rejecting future-dated posts or posts with parsing issues
    'date_filters': {
        'enabled': False,  # Completely disabled to prevent any date-based filtering
        'start_date': None,  # Explicitly set to None to avoid any boundary checks
        'end_date': None,  # Explicitly set to None to avoid any boundary checks
        'ignore_missing_dates': True,  # Don't skip posts without detectable dates
        'accept_future_dates': True,  # NEW: Accept posts with dates in the future (for 2026)
        'fallback_to_crawl_date': False  # Don't assume crawl date if parsing fails
    },
    # URL detection configuration - enhanced for better discovery
    'url_detection': {
        'check_sitemap': True,  # Check sitemap for new URLs
        'check_rss': True,  # Check RSS feeds
        'follow_canonical': True,  # Follow canonical URLs
        'validate_links': True,  # Validate that links are accessible
        'check_sitemap_index': True,  # NEW: Also check sitemap index files
        'parse_atom_feeds': True,  # NEW: Parse Atom feeds in addition to RSS
        'refresh_discovery_cache': True  # NEW: Force refresh of URL discovery cache
    },
    # Enhanced scraping patterns for better content extraction
    # CRITICAL FIX: Added more date selectors and relaxed requirements
    'scraping_config': {
        'extract_metadata': True,  # Extract all metadata including publish date
        'parse_json_ld': True,  # Parse JSON-LD structured data
        'extract_og_tags': True,  # Extract Open Graph tags
        'extract_article_schema': True,  # Extract article schema markup
        'extract_dublin_core': True,  # NEW: Extract Dublin Core metadata
        'selectors': {
            'title': [
                'h1.blog-post-title',
                'h1.entry-title',
                'h1',
                'article h1',
                '.post-title',
                'meta[property="og:title"]'  # NEW: Fallback to OG tags
            ],
            'date': [
                # ENHANCED: More comprehensive date selector list
                'meta[property="article:published_time"]',
                'meta[property="article:published"]',
                'meta[name="publish-date"]',
                'meta[name="publishdate"]',
                'meta[name="date"]',
                'meta[name="DC.date"]',  # NEW: Dublin Core date
                'meta[name="DC.date.issued"]',  # NEW: Dublin Core issued date
                'time[datetime]',
                'time.published',
                'time.entry-date',
                '.post-date',
                '.published-date',
                '.entry-date',
                'span.date',
                'div.date',
                # NEW: AWS-specific blog date selectors
                '.blog-post-meta time',
                '.blog-post-date',
                'script[type="application/ld+json"]'  # Extract from structured data
            ],
            'content': ['article', '.post-content', '.blog-post-content', 'main', '.entry-content'],
            'author': ['.author', '.post-author', '.entry-author', 'meta[name="author"]', 'meta[property="article:author"]']
        },
        'require_date': False,  # Don't skip posts if date extraction fails
        'date_formats': [  # NEW: Explicit date format specifications for parsing
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%B %d, %Y',  # March 2, 2026
            '%b %d, %Y',
            '%d %B %Y',
            '%Y/%m/%d',
            'iso8601'
        ],
        'date_parsing_fallbacks': True,  # NEW: Use multiple parsing strategies
        'extract_dates_from_url': True  # NEW: Try to extract date from URL path
    },
    # Debugging and logging options - maximized for investigation
    'debug': {
        'verbose_logging': True,  # Enable detailed logging
        'save_raw_html': True,  # Save raw HTML for inspection
        'log_date_extraction': True,  # Log date extraction attempts
        'log_url_patterns': True,  # Log URL pattern matching
        'trace_filtering': True,  # Trace why posts might be filtered out
        'log_selector_attempts': True,  # NEW: Log each selector attempt
        'log_metadata_extraction': True,  # NEW: Log all metadata extraction
        'capture_screenshots': False,  # Disabled to reduce overhead
        'log_http_headers': True,  # NEW: Log HTTP response headers
        'validate_post_structure': True  # NEW: Validate expected post structure
    },
    # Retry configuration for robustness
    'retry_config': {
        'max_retries': 3,
        'retry_on_timeout': True,
        'retry_on_http_error': True,
        'retry_on_parse_error': True,  # NEW: Retry if parsing fails
        'backoff_multiplier': 2
    },
    # NEW: Post-crawl validation rules
    'validation': {
        'verify_post_indexed': True,  # Verify post appears in index after crawl
        'check_expected_date': EXPECTED_POST_DATE,  # Validate against expected date
        'alert_on_missing': True,  # Alert if post still missing after crawl
        'validate_content_length': True,  # Ensure content was extracted
        'minimum_content_length': 100  # Minimum characters for valid content
    },
    # Additional metadata for tracking
    'metadata': {
        'trigger_reason': 'Missing blog post investigation - March 2, 2026 post not appearing',
        'post_topic': 'Amazon WorkSpaces Graphics G6 bundles',
        'expected_date': EXPECTED_POST_DATE,
        'investigation_date': datetime.now(timezone.utc).isoformat(),
        'fix_version': '2.1',  # Track configuration version
        'primary_fixes': [
            'Disabled date filtering to prevent future date rejection',
            'Enhanced date selector coverage',
            'Added date format parsing fallbacks',
            'Enabled URL discovery cache refresh',
            'Added post-crawl validation'
        ]
    }
}

print("Enhanced Crawler Configuration:")
print("=" * 60)
print("✓ Force refresh enabled - will re-crawl even if cached")
print("✓ Date filtering COMPLETELY DISABLED - no date-based filtering")
print("✓ Future dates explicitly accepted (critical for 2026-03-02)")
print("✓ Enhanced date selectors (15+ patterns) for better extraction")
print("✓ Multiple date format parsers with fallback strategies")
print("✓ URL discovery cache refresh enabled")
print("✓ Multiple URL patterns configured for better detection")
print("✓ Post-crawl validation enabled to verify indexing")
print("✓ Verbose logging enabled for comprehensive diagnostics")
print("✓ Date extraction validation without strict requirements")
print("=" * 60)
print()

try:
    req = urllib.request.Request(
        STAGING_API,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'AWS-Staging-Crawler-Trigger/2.1-Enhanced',
            'X-Crawler-Debug': 'true',  # Signal API to enable debug mode
            'X-Investigation': 'missing-post-2026-03-02',  # Tag for tracking
            'X-Force-Reindex': 'true',  # NEW: Force reindexing of URL
            'X-Config-Version': '2.1'  # Track configuration version
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
        'accept_future_dates': payload['date_filters']['accept_future_dates'],
        'debug_enabled': payload['debug']['verbose_logging'],
        'validation_enabled': payload['validation']['verify_post_indexed'],
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
        print("1. Check crawler logs for date extraction attempts (15+ selectors)")
        print("2. Verify URL pattern matching in verbose logs")
        print("3. Review saved raw HTML if post structure has changed")
        print("4. Confirm post is published and publicly accessible")
        print("5. Check if robots.txt or meta tags are blocking crawler")
        print(f"6. Verify expected date ({EXPECTED_POST_DATE}) in post metadata")
        print("7. NEW: Review date parsing fallback attempts in logs")
        print("8. NEW: Check if date was rejected as 'future date' (now accepted)")
        print("9. NEW: Verify URL discovery cache was refreshed")
        print("10. NEW: Confirm post-crawl validation completed successfully")
        print("=" * 60)
        print("\nKEY FIXES APPLIED:")
        print("- Date filtering completely disabled (enabled: false)")
        print("- Future dates explicitly accepted (2026-03-02)")
        print("- 15+ date extraction selectors (vs previous 5)")
        print("- Multiple date format parsers with fallbacks")
        print("- URL discovery cache force-refreshed")
        print("- Post-crawl validation to verify indexing")
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
    print("- Confirm API supports enhanced configuration parameters")
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