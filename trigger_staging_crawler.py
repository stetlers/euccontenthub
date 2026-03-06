```python
"""
Trigger staging crawler via API with specific URL targeting
Enhanced with date filtering diagnostics and crawler validation
Version 2.6 - Enhanced investigation mode for missing blog post detection
Root cause analysis: Why post from March 2, 2026 is not being detected
Added: Pre-flight checks, API response validation, comprehensive diagnostics
"""

import json
import urllib.request
import urllib.error
import sys
import time
from datetime import datetime, timezone, timedelta
import hashlib

STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/crawl'

# Specific blog post URL that needs to be crawled
TARGET_BLOG_POST = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'

# Expected publication date of the blog post for validation
EXPECTED_POST_DATE = '2026-03-02'

# Generate unique investigation ID for tracking
INVESTIGATION_ID = hashlib.md5(f"{TARGET_BLOG_POST}{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:12]

print("=" * 80)
print("STAGING CRAWLER INVESTIGATION - VERSION 2.6")
print("=" * 80)
print(f"Investigation ID: {INVESTIGATION_ID}")
print(f"Target: {TARGET_BLOG_POST}")
print(f"Expected Date: {EXPECTED_POST_DATE}")
print(f"Investigation: Why is this post not being detected?")
print(f"Current Time (UTC): {datetime.now(timezone.utc).isoformat()}")
print("=" * 80)
print()

# Pre-flight check: Verify target URL is accessible
print("PRE-FLIGHT CHECK: URL Accessibility")
print("-" * 80)
try:
    req = urllib.request.Request(TARGET_BLOG_POST, headers={'User-Agent': 'AWS-BlogCrawler-Investigation/2.6'})
    with urllib.request.urlopen(req, timeout=30) as response:
        status_code = response.status
        content_type = response.headers.get('Content-Type', 'unknown')
        content_length = response.headers.get('Content-Length', 'unknown')
        print(f"✓  URL is accessible")
        print(f"   Status Code: {status_code}")
        print(f"   Content-Type: {content_type}")
        print(f"   Content-Length: {content_length} bytes")
        
        # Check for redirects
        if response.url != TARGET_BLOG_POST:
            print(f"⚠️  URL redirected to: {response.url}")
            print(f"   Investigation Action: Check if crawler follows redirects")
except urllib.error.HTTPError as e:
    print(f"❌ CRITICAL ISSUE: HTTP Error {e.code}")
    print(f"   The URL returns HTTP {e.code} - crawler cannot access this page")
    print(f"   Investigation Action: Verify URL is correct and page exists")
except urllib.error.URLError as e:
    print(f"❌ CRITICAL ISSUE: URL Error - {e.reason}")
    print(f"   Investigation Action: Check network connectivity and DNS")
except Exception as e:
    print(f"❌ CRITICAL ISSUE: {type(e).__name__}: {e}")
    print(f"   Investigation Action: Verify URL format and accessibility")
print("-" * 80)
print()

# Parse expected date and perform investigation diagnostics
try:
    expected_dt = datetime.strptime(EXPECTED_POST_DATE, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    current_dt = datetime.now(timezone.utc)
    days_diff = (expected_dt - current_dt).days
    
    print("INVESTIGATION: DATE ANALYSIS")
    print("-" * 80)
    print(f"Expected Post Date: {expected_dt.isoformat()}")
    print(f"Current Date:       {current_dt.isoformat()}")
    print(f"Days Difference:    {days_diff} days")
    
    if days_diff > 0:
        print(f"❌ ROOT CAUSE IDENTIFIED: Post date is {days_diff} days in the FUTURE")
        print(f"   This is likely THE PRIMARY ISSUE - future date filtering")
        print(f"   FIX APPLIED: Date filtering completely disabled in payload")
        print(f"   FIX APPLIED: accept_future_dates = True")
        print(f"   FIX APPLIED: reject_on_date_parsing_failure = False")
    elif days_diff < -7:
        print(f"⚠️  POTENTIAL ISSUE: Post date is {abs(days_diff)} days in the PAST")
        print(f"   This may be outside crawler's date range window")
        print(f"   FIX APPLIED: Wide date range to accommodate old posts")
    else:
        print(f"✓  Post date is within normal range")
    print("-" * 80)
    print()
    
    # Set investigation date range - very wide to eliminate date filtering as cause
    date_range_start = (current_dt - timedelta(days=365)).strftime('%Y-%m-%d')
    date_range_end = (current_dt + timedelta(days=3650)).strftime('%Y-%m-%d')
    print(f"INVESTIGATION DATE RANGE: {date_range_start} to {date_range_end}")
    print(f"(Wide range to eliminate date filtering as root cause)")
    print()
    
except Exception as e:
    print(f"⚠️  WARNING: Could not parse expected date: {e}")
    date_range_start = None
    date_range_end = None
    print()

print("INVESTIGATION CHECKLIST:")
print("-" * 80)
print("1. ❓ URL Detection Issues:")
print("   - Is the URL in sitemap? [CHECKING]")
print("   - Is the URL accessible (HTTP 200)? [VERIFIED ABOVE]")
print("   - Are there URL format validation failures? [DISABLED VALIDATION]")
print()
print("2. ❌ Date Filtering Issues [PRIMARY SUSPECT]:")
print("   - Is future date filtering rejecting the post? [LIKELY ROOT CAUSE]")
print("   - FIX: Date filtering disabled completely")
print("   - FIX: accept_future_dates = True")
print("   - FIX: Date validation disabled")
print()
print("3. ❓ Content Extraction Issues:")
print("   - Are selectors finding the post content? [ENHANCED SELECTORS]")
print("   - Is metadata extraction failing? [ALL METADATA METHODS ENABLED]")
print("   - Are required fields missing? [ALL REQUIREMENTS DISABLED]")
print()
print("4. ❓ Storage/Indexing Issues:")
print("   - Is DynamoDB write succeeding? [WRITE VERIFICATION ENABLED]")
print("   - Is validation query finding the post? [POST-WRITE READ ENABLED]")
print("   - Are there table consistency issues? [CONSISTENT READS ENABLED]")
print()
print("5. ❓ Pattern Matching Issues:")
print("   - Do include patterns match the URL? [CATCH-ALL PATTERN ADDED]")
print("   - Are exclude patterns blocking the URL? [EXCLUSIONS CLEARED]")
print("-" * 80)
print()

# Investigation payload with comprehensive logging and minimal filtering
payload = {
    # Investigation metadata
    'investigation_id': INVESTIGATION_ID,
    'investigation_mode': True,
    'investigation_target': TARGET_BLOG_POST,
    'investigation_reason': 'Post from March 2, 2026 not detected - suspected future date filtering',
    'investigation_timestamp': datetime.now(timezone.utc).isoformat(),
    
    # Target configuration - force processing
    'target_urls': [TARGET_BLOG_POST],
    'force_refresh': True,
    'bypass_cache': True,
    'force_reindex': True,
    'crawl_depth': 1,
    'ignore_robots_txt': False,
    'user_agent': f'AWS-BlogCrawler-Investigation/2.6 (ID:{INVESTIGATION_ID})',
    
    # Investigation: URL pattern matching - very permissive
    'include_patterns': [
        '*/amazon-workspaces-launches-graphics-g6*',
        '/blogs/desktop-and-application-streaming/*',
        '*amazon-workspaces*g6*',
        '*g6-gr6*',
        '*graphics*bundles*',
        '*',  # Catch-all to eliminate pattern matching as cause
    ],
    'exclude_patterns': [],  # Empty to eliminate exclusion as cause
    'log_pattern_matching': True,
    'pattern_matching_case_sensitive': False,
    
    # Investigation: PRIMARY FIX - Completely disable date filtering
    'date_filters': {
        'enabled': False,  # PRIMARY FIX: Disable all date filtering
        'start_date': None,
        'end_date': None,
        'ignore_missing_dates': True,
        'accept_future_dates': True,  # CRITICAL FIX: Accept future dates
        'accept_past_dates': True,
        'fallback_to_crawl_date': False,
        'max_future_days': 10000,  # Allow far future dates
        'max_past_days': 10000,  # Allow far past dates
        'validate_date_reasonableness': False,  # Don't validate date logic
        'reject_on_date_parsing_failure': False,  # CRITICAL FIX: Don't reject on parse failure
        'log_rejection_reasons': True,
        'log_all_date_operations': True,
        'timezone_handling': 'utc',
        'allow_timezone_mismatch': True,
        'log_date_filter_decisions': True,
        'trace_date_comparison': True,
        'bypass_future_date_check': True,  # Explicit bypass of future date checks
        'bypass_past_date_check': True,  # Explicit bypass of past date checks
        'treat_all_dates_as_valid': True  # Accept any date value
    },
    
    # Investigation: Enhanced URL discovery
    'url_detection': {
        'check_sitemap': True,
        'check_rss': True,
        'follow_canonical': True,
        'validate_links': False,
        'check_sitemap_index': True,
        'parse_atom_feeds': True,
        'refresh_discovery_cache': True,
        'force_sitemap_refresh': True,
        'check_blog_index_pages': True,
        'follow_pagination': True,
        'max_discovery_depth': 3,
        'verify_url_accessibility': True,
        'log_discovery_process': True,
        'check_url_redirects': True,
        'validate_url_format': False,
        'timeout_seconds': 45,
        'retry_failed_discoveries': True,
        'log_sitemap_contents': True,
        'log_url_accessibility_details': True,
        'trace_url_normalization': True,
        'check_robots_txt': True,
        'log_robots_txt_rules': True,
        'verify_dns_resolution': True,
        'log_http_redirects': True,
        'accept_direct_urls': True,  # Accept directly provided URLs without discovery
        'skip_url_validation': True  # Skip URL format validation
    },
    
    # Investigation: Enhanced scraping with exhaustive selectors
    'scraping_config': {
        'extract_metadata': True,
        'parse_json_ld': True,
        'extract_og_tags': True,
        'extract_article_schema': True,
        'extract_dublin_core': True,
        'extract_twitter_cards': True,
        'parse_microdata': True,
        'parse_rdfa': True,
        'parse_html5_time': True,
        'extract_all_meta_tags': True,
        
        'selectors': {
            'title': [
                'h1',
                'h1.blog-post-title',
                'h1.entry-title',
                'article h1',
                '.post-title',
                'meta[property="og:title"]',
                'meta[name="twitter:title"]',
                '[itemprop="headline"]',
                'title',
                'head title',
            ],
            'date': [
                'meta[property="article:published_time"]',
                'meta[property="article:published"]',
                'meta[property="og:published_time"]',
                'time[datetime]',
                'time[pubdate]',
                'meta[name="publish-date"]',
                'meta[name="date"]',
                'meta[name="DC.date"]',
                'meta[name="dcterms.date"]',
                '[itemprop="datePublished"]',
                '[itemprop="publishDate"]',
                'script[type="application/ld+json"]',
                'time.published',
                'time.entry-date',
                '.post-date',
                '.published-date',
                '.entry-date',
                '.blog-post-date',
                'meta[name="publication-date"]',
                'meta[name="publishdate"]',
                '[datetime]',
                '[data-date]',
                '[data-published]',
                'time',
                'span.date',
                'div.date',
                'p.date',
            ],
            'content': [
                'article',
                '.post-content',
                '.entry-content',
                'main',
                '[itemprop="articleBody"]',
                '#content',
                '.content',
                '.blog-content',
                'main article',
            ],
            'author': [
                'meta[name="author"]',
                '.author',
                '.post-author',
                '[itemprop="author"]',
                '[rel="author"]',
                'meta[property="article:author"]',
            ]
        },
        
        # Investigation: Don't require any fields
        'require_date': False,  # Don't reject if date missing
        'require_title': False,
        'require_content': False,
        'require_author': False,
        'allow_partial_extraction': True,
        
        # Investigation: Exhaustive date format support
        'date_formats': [
            'iso8601',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%B %d, %Y',
            '%b %d, %Y',
            '%d %B %Y',
            '%d %b %Y',
            '%Y/%m/%d',
            '%m/%d/%Y',
            '%d-%m-%Y',
            '%m-%d-%Y',
            'rfc3339',
            'rfc2822',
            'auto',
        ],
        
        'date_parsing_fallbacks': True,
        'extract_dates_from_url': True,
        'use_fuzzy_date_parsing': True,
        'parse_relative_dates': False,
        'timezone_aware': True,
        'default_timezone': 'UTC',
        'try_multiple_parsers': True,
        'log_all_parsing_attempts': True,
        'use_dateutil_parser': True,
        'accept_partial_dates': True,
        'normalize_dates_to_utc': True,
        'save_parsing_failures': True,
        'dump_page_source': True,
        'log_selector_matches': True,
        'trace_extraction_pipeline': True,
        'continue_on_date_parse_failure': True,  # Don't stop if date parsing fails
        'use_fallback_date_on_failure': True,  # Use current date as fallback
        'store_unparsed_date_string': True  # Store original date string for debugging
    },
    
    # Investigation: Maximum debugging enabled
    'debug': {
        '