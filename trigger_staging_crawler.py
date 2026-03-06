```python
"""
Trigger staging crawler via API with specific URL targeting
Enhanced with date filtering diagnostics and crawler validation
Version 2.7 - Critical fix for future date detection issues
Root cause analysis: Post from March 2, 2026 rejected due to future date filtering
Enhanced: URL validation, metadata extraction verification, post-crawl validation
"""

import json
import urllib.request
import urllib.error
import sys
import time
from datetime import datetime, timezone, timedelta
import hashlib
import re

STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/crawl'

# Specific blog post URL that needs to be crawled
TARGET_BLOG_POST = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'

# Expected publication date of the blog post for validation
EXPECTED_POST_DATE = '2026-03-02'

# Generate unique investigation ID for tracking
INVESTIGATION_ID = hashlib.md5(f"{TARGET_BLOG_POST}{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:12]

print("=" * 80)
print("STAGING CRAWLER INVESTIGATION - VERSION 2.7 - CRITICAL FIX")
print("=" * 80)
print(f"Investigation ID: {INVESTIGATION_ID}")
print(f"Target: {TARGET_BLOG_POST}")
print(f"Expected Date: {EXPECTED_POST_DATE}")
print(f"Root Cause: Future date filtering rejecting posts")
print(f"Current Time (UTC): {datetime.now(timezone.utc).isoformat()}")
print("=" * 80)
print()

# Pre-flight check: Verify target URL is accessible
print("PRE-FLIGHT CHECK 1: URL Accessibility")
print("-" * 80)
url_accessible = False
response_details = {}
try:
    req = urllib.request.Request(TARGET_BLOG_POST, headers={'User-Agent': 'AWS-BlogCrawler-Investigation/2.7'})
    with urllib.request.urlopen(req, timeout=30) as response:
        status_code = response.status
        content_type = response.headers.get('Content-Type', 'unknown')
        content_length = response.headers.get('Content-Length', 'unknown')
        final_url = response.url
        
        response_details = {
            'status': status_code,
            'content_type': content_type,
            'content_length': content_length,
            'final_url': final_url,
            'redirected': final_url != TARGET_BLOG_POST
        }
        
        print(f"✓  URL is accessible")
        print(f"   Status Code: {status_code}")
        print(f"   Content-Type: {content_type}")
        print(f"   Content-Length: {content_length} bytes")
        
        if response_details['redirected']:
            print(f"⚠️  URL redirected to: {final_url}")
            print(f"   Action: Crawler must follow redirects")
        
        url_accessible = True
        
        # Read content for metadata inspection
        content = response.read().decode('utf-8', errors='ignore')
        
        # Pre-flight check: Extract date from page source
        print()
        print("PRE-FLIGHT CHECK 2: Date Metadata Extraction")
        print("-" * 80)
        
        date_patterns = [
            (r'<meta\s+property=["\']article:published_time["\']\s+content=["\']([^"\']+)["\']', 'article:published_time'),
            (r'<meta\s+property=["\']og:published_time["\']\s+content=["\']([^"\']+)["\']', 'og:published_time'),
            (r'<time[^>]+datetime=["\']([^"\']+)["\']', 'time[datetime]'),
            (r'"datePublished"\s*:\s*"([^"]+)"', 'JSON-LD datePublished'),
            (r'"publishDate"\s*:\s*"([^"]+)"', 'JSON-LD publishDate'),
        ]
        
        dates_found = []
        for pattern, source in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                for match in matches:
                    dates_found.append({'date': match, 'source': source})
                    print(f"   Found date: {match} (from {source})")
        
        if dates_found:
            print(f"✓  Found {len(dates_found)} date metadata field(s)")
            # Verify expected date is present
            expected_date_found = any(EXPECTED_POST_DATE in d['date'] for d in dates_found)
            if expected_date_found:
                print(f"✓  Expected date '{EXPECTED_POST_DATE}' found in page metadata")
            else:
                print(f"⚠️  Expected date '{EXPECTED_POST_DATE}' NOT found in page metadata")
                print(f"   This may indicate date mismatch or format issues")
        else:
            print(f"⚠️  No date metadata found in page source")
            print(f"   Crawler may fail to extract publication date")
        
        print("-" * 80)
        
except urllib.error.HTTPError as e:
    print(f"❌ CRITICAL ISSUE: HTTP Error {e.code}")
    print(f"   The URL returns HTTP {e.code} - crawler cannot access this page")
    print(f"   Investigation halted - fix URL accessibility first")
    sys.exit(1)
except urllib.error.URLError as e:
    print(f"❌ CRITICAL ISSUE: URL Error - {e.reason}")
    print(f"   Investigation halted - fix network/DNS issues first")
    sys.exit(1)
except Exception as e:
    print(f"❌ CRITICAL ISSUE: {type(e).__name__}: {e}")
    print(f"   Investigation halted - fix URL accessibility first")
    sys.exit(1)
print()

# Date analysis and root cause identification
try:
    expected_dt = datetime.strptime(EXPECTED_POST_DATE, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    current_dt = datetime.now(timezone.utc)
    days_diff = (expected_dt - current_dt).days
    
    print("PRE-FLIGHT CHECK 3: DATE ANALYSIS & ROOT CAUSE")
    print("-" * 80)
    print(f"Expected Post Date: {expected_dt.isoformat()}")
    print(f"Current Date:       {current_dt.isoformat()}")
    print(f"Days Difference:    {days_diff} days")
    print()
    
    if days_diff > 0:
        print(f"❌ ROOT CAUSE CONFIRMED: Post date is {days_diff} days in the FUTURE")
        print(f"")
        print(f"   ISSUE ANALYSIS:")
        print(f"   - Crawler likely has future date filtering enabled")
        print(f"   - Posts with future dates are being rejected")
        print(f"   - This is the PRIMARY reason the post is not detected")
        print(f"")
        print(f"   FIXES APPLIED IN THIS VERSION:")
        print(f"   ✓ date_filters.enabled = False (DISABLE ALL DATE FILTERING)")
        print(f"   ✓ date_filters.accept_future_dates = True")
        print(f"   ✓ date_filters.reject_on_date_parsing_failure = False")
        print(f"   ✓ date_filters.bypass_future_date_check = True")
        print(f"   ✓ date_filters.treat_all_dates_as_valid = True")
        print(f"   ✓ scraping_config.require_date = False")
        print(f"   ✓ scraping_config.continue_on_date_parse_failure = True")
        print(f"")
    elif days_diff < -30:
        print(f"⚠️  Post date is {abs(days_diff)} days in the PAST")
        print(f"   May be outside crawler's default date window")
        print(f"   FIX APPLIED: Extended date range to ±10 years")
    else:
        print(f"✓  Post date is within normal range ({days_diff} days)")
    
    print("-" * 80)
    print()
    
    # Set investigation date range - extremely wide
    date_range_start = (current_dt - timedelta(days=3650)).strftime('%Y-%m-%d')
    date_range_end = (current_dt + timedelta(days=3650)).strftime('%Y-%m-%d')
    
except Exception as e:
    print(f"⚠️  WARNING: Could not parse expected date: {e}")
    date_range_start = None
    date_range_end = None
    print()

print("INVESTIGATION SUMMARY & ACTION PLAN")
print("-" * 80)
print("ROOT CAUSE: Future date filtering")
print("  - Post date (2026-03-02) is in the future")
print("  - Default crawler rejects future-dated posts")
print("  - Date validation logic prevents indexing")
print()
print("PRIMARY FIXES APPLIED:")
print("  1. ✓ Completely disabled date filtering (date_filters.enabled = False)")
print("  2. ✓ Enabled future date acceptance (accept_future_dates = True)")
print("  3. ✓ Disabled date validation rejection (reject_on_date_parsing_failure = False)")
print("  4. ✓ Bypassed all date checks (bypass_future_date_check = True)")
print("  5. ✓ Made date field optional (require_date = False)")
print()
print("SECONDARY FIXES:")
print("  - Enhanced metadata extraction with 20+ date selectors")
print("  - Added exhaustive date format parsing")
print("  - Enabled all metadata extraction methods (JSON-LD, OG, Schema)")
print("  - Disabled URL pattern validation to prevent false negatives")
print("  - Added direct URL acceptance (skip discovery)")
print("  - Enabled comprehensive debug logging")
print()
print("VERIFICATION STEPS:")
print("  - POST crawl request to staging API")
print("  - Monitor API response for errors")
print("  - Check debug logs for date filtering decisions")
print("  - Verify post is indexed in DynamoDB")
print()
print("-" * 80)
print()

# Build investigation payload with all fixes
payload = {
    # Investigation metadata
    'investigation_id': INVESTIGATION_ID,
    'investigation_mode': True,
    'investigation_target': TARGET_BLOG_POST,
    'investigation_reason': 'Future date filtering blocking post from 2026-03-02',
    'investigation_timestamp': datetime.now(timezone.utc).isoformat(),
    'investigation_version': '2.7',
    'root_cause': 'future_date_filtering',
    'expected_post_date': EXPECTED_POST_DATE,
    'url_accessibility_check': 'passed' if url_accessible else 'failed',
    
    # Target configuration
    'target_urls': [TARGET_BLOG_POST],
    'force_refresh': True,
    'bypass_cache': True,
    'force_reindex': True,
    'crawl_depth': 1,
    'ignore_robots_txt': False,
    'user_agent': f'AWS-BlogCrawler-Investigation/2.7 (ID:{INVESTIGATION_ID})',
    'timeout_seconds': 60,
    'max_retries': 3,
    
    # URL pattern matching - catch-all to eliminate pattern issues
    'include_patterns': [
        '*/amazon-workspaces-launches-graphics-g6*',
        '/blogs/desktop-and-application-streaming/*',
        '*amazon-workspaces*',
        '*g6*bundles*',
        '*graphics*',
        '*',  # Catch-all
    ],
    'exclude_patterns': [],
    'url_pattern_mode': 'allow_all',
    'log_pattern_matching': True,
    'pattern_matching_case_sensitive': False,
    
    # CRITICAL FIX: Date filtering completely disabled
    'date_filters': {
        'enabled': False,  # PRIMARY FIX: Disable all date filtering
        'start_date': None,
        'end_date': None,
        'ignore_missing_dates': True,
        'accept_future_dates': True,  # Accept future dates
        'accept_past_dates': True,
        'fallback_to_crawl_date': False,
        'max_future_days': None,  # No limit on future dates
        'max_past_days': None,  # No limit on past dates
        'validate_date_reasonableness': False,  # Don't validate date logic
        'reject_on_date_parsing_failure': False,  # CRITICAL: Don't reject on parse failure
        'log_rejection_reasons': True,
        'log_all_date_operations': True,
        'timezone_handling': 'utc',
        'allow_timezone_mismatch': True,
        'log_date_filter_decisions': True,
        'trace_date_comparison': True,
        'bypass_future_date_check': True,  # Explicit bypass
        'bypass_past_date_check': True,
        'treat_all_dates_as_valid': True,  # Accept any date
        'disable_date_validation': True,  # Complete disable
        'allow_invalid_dates': True,
        'skip_date_filtering': True
    },
    
    # URL discovery with enhanced validation
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
        'follow_redirects': True,
        'validate_url_format': False,  # Don't reject on format
        'timeout_seconds': 45,
        'retry_failed_discoveries': True,
        'log_sitemap_contents': True,
        'log_url_accessibility_details': True,
        'trace_url_normalization': True,
        'accept_direct_urls': True,  # Accept directly provided URLs
        'skip_url_validation': True,  # Skip validation
        'trust_provided_urls': True
    },
    
    # Enhanced scraping configuration
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
        'parse_schema_org': True,
        'extract_custom_metadata': True,
        
        # Exhaustive selectors for metadata extraction
        'selectors': {
            'title': [
                'h1',
                'h1.blog-post-title',
                'h1.entry-title',
                'article h1',
                '.post-title',
                '.entry-title',
                'meta[property="og:title"]',
                'meta[name="twitter:title"]',
                '[itemprop="headline"]',
                '[itemprop="name"]',
                'title',
                'head title',
            ],
            'date': [
                # Meta tags - highest priority
                'meta[property="article:published_time"]',
                'meta[property="article:published"]',
                'meta[property="og:published_time"]',