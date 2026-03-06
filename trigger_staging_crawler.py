```python
"""
Trigger staging crawler via API with specific URL targeting
Enhanced with date filtering diagnostics and crawler validation
Version 2.2 - Additional fixes for March 2, 2026 post detection
"""

import json
import urllib.request
import sys
from datetime import datetime, timezone, timedelta

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

# Parse expected date to validate it's in the future
try:
    expected_dt = datetime.strptime(EXPECTED_POST_DATE, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    current_dt = datetime.now(timezone.utc)
    days_diff = (expected_dt - current_dt).days
    
    if days_diff > 0:
        print(f"⚠️  NOTE: Expected post date is {days_diff} days in the future")
        print(f"    Ensuring future date acceptance is enabled in crawler config\n")
    elif days_diff < -30:
        print(f"⚠️  NOTE: Expected post date is {abs(days_diff)} days in the past")
        print(f"    Verifying date range filters are properly configured\n")
except Exception as e:
    print(f"⚠️  WARNING: Could not parse expected date: {e}\n")

# Prepare payload with target URL and crawler options
# Enhanced payload to address potential date filtering and scraping issues
payload = {
    'target_urls': [TARGET_BLOG_POST],
    'force_refresh': True,  # Force re-crawl even if URL was previously visited
    'bypass_cache': True,  # NEW: Bypass all caching layers (URL cache, content cache, etc.)
    'force_reindex': True,  # NEW: Force reindexing in DynamoDB even if record exists
    'crawl_depth': 1,
    'include_patterns': [
        '/blogs/desktop-and-application-streaming/*',
        '/blogs/*/amazon-workspaces-*',  # Additional pattern for WorkSpaces posts
        '*/amazon-workspaces-launches-*'  # NEW: More specific pattern for this post
    ],
    # CRITICAL FIX: Date filtering completely disabled to ensure March 2, 2026 post is captured
    # Previous issue: Date filter may have been rejecting future-dated posts or posts with parsing issues
    'date_filters': {
        'enabled': False,  # Completely disabled to prevent any date-based filtering
        'start_date': None,  # Explicitly set to None to avoid any boundary checks
        'end_date': None,  # Explicitly set to None to avoid any boundary checks
        'ignore_missing_dates': True,  # Don't skip posts without detectable dates
        'accept_future_dates': True,  # Accept posts with dates in the future (for 2026)
        'accept_past_dates': True,  # NEW: Explicitly accept past dates as well
        'fallback_to_crawl_date': False,  # Don't assume crawl date if parsing fails
        'max_future_days': 3650,  # NEW: Accept dates up to 10 years in future (defensive)
        'validate_date_reasonableness': False  # NEW: Don't reject "unreasonable" dates
    },
    # URL detection configuration - enhanced for better discovery
    'url_detection': {
        'check_sitemap': True,  # Check sitemap for new URLs
        'check_rss': True,  # Check RSS feeds
        'follow_canonical': True,  # Follow canonical URLs
        'validate_links': True,  # Validate that links are accessible
        'check_sitemap_index': True,  # Check sitemap index files
        'parse_atom_feeds': True,  # Parse Atom feeds in addition to RSS
        'refresh_discovery_cache': True,  # Force refresh of URL discovery cache
        'force_sitemap_refresh': True,  # NEW: Force refresh sitemap cache specifically
        'check_blog_index_pages': True,  # NEW: Check blog category/archive index pages
        'follow_pagination': True,  # NEW: Follow pagination on blog index pages
        'max_discovery_depth': 3  # NEW: Allow deeper discovery for hard-to-find posts
    },
    # Enhanced scraping patterns for better content extraction
    # CRITICAL FIX: Added more date selectors and relaxed requirements
    'scraping_config': {
        'extract_metadata': True,  # Extract all metadata including publish date
        'parse_json_ld': True,  # Parse JSON-LD structured data
        'extract_og_tags': True,  # Extract Open Graph tags
        'extract_article_schema': True,  # Extract article schema markup
        'extract_dublin_core': True,  # Extract Dublin Core metadata
        'extract_twitter_cards': True,  # NEW: Extract Twitter card metadata
        'parse_microdata': True,  # NEW: Parse HTML5 microdata
        'parse_rdfa': True,  # NEW: Parse RDFa attributes
        'selectors': {
            'title': [
                'h1.blog-post-title',
                'h1.entry-title',
                'h1',
                'article h1',
                '.post-title',
                'meta[property="og:title"]',
                'meta[name="twitter:title"]',  # NEW: Twitter card title
                'meta[name="title"]',  # NEW: Generic title meta
                '[itemprop="headline"]'  # NEW: Schema.org headline
            ],
            'date': [
                # ENHANCED: More comprehensive date selector list with AWS-specific patterns
                'meta[property="article:published_time"]',
                'meta[property="article:published"]',
                'meta[name="publish-date"]',
                'meta[name="publishdate"]',
                'meta[name="publication-date"]',  # NEW
                'meta[name="date"]',
                'meta[name="DC.date"]',
                'meta[name="DC.date.issued"]',
                'meta[name="DC.date.created"]',  # NEW
                'meta[name="dcterms.created"]',  # NEW
                'meta[property="article:modified_time"]',  # NEW: Fallback to modified time
                'time[datetime]',
                'time[pubdate]',  # NEW
                'time.published',
                'time.entry-date',
                'time.updated',  # NEW
                '.post-date',
                '.published-date',
                '.entry-date',
                '.publication-date',  # NEW
                'span.date',
                'div.date',
                # AWS-specific blog date selectors
                '.blog-post-meta time',
                '.blog-post-date',
                '.blog-post-metadata time',  # NEW
                '.aws-blog-date',  # NEW
                '.post-meta time',  # NEW
                '[itemprop="datePublished"]',  # NEW: Schema.org date
                '[itemprop="dateCreated"]',  # NEW
                'script[type="application/ld+json"]'  # Extract from structured data
            ],
            'content': [
                'article',
                '.post-content',
                '.blog-post-content',
                '.entry-content',
                'main',
                '.main-content',  # NEW
                '[itemprop="articleBody"]',  # NEW: Schema.org article body
                '.aws-blog-content'  # NEW: AWS-specific content class
            ],
            'author': [
                '.author',
                '.post-author',
                '.entry-author',
                '.blog-author',  # NEW
                'meta[name="author"]',
                'meta[property="article:author"]',
                '[itemprop="author"]',  # NEW
                '[rel="author"]'  # NEW
            ]
        },
        'require_date': False,  # Don't skip posts if date extraction fails
        'require_title': False,  # NEW: Don't skip posts if title extraction fails
        'require_content': False,  # NEW: Don't skip posts if content extraction fails (for debugging)
        'date_formats': [
            # Explicit date format specifications for parsing
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%SZ',  # NEW: Zulu time format
            '%Y-%m-%dT%H:%M:%S.%fZ',  # NEW
            '%B %d, %Y',  # March 2, 2026
            '%b %d, %Y',
            '%d %B %Y',
            '%d %b %Y',  # NEW
            '%Y/%m/%d',
            '%m/%d/%Y',  # NEW
            '%d-%m-%Y',  # NEW
            'iso8601',
            'rfc3339',  # NEW
            'rfc2822'  # NEW
        ],
        'date_parsing_fallbacks': True,  # Use multiple parsing strategies
        'extract_dates_from_url': True,  # Try to extract date from URL path
        'use_fuzzy_date_parsing': True,  # NEW: Use fuzzy parsing as last resort
        'parse_relative_dates': True,  # NEW: Parse relative dates like "2 days ago"
        'timezone_aware': True  # NEW: Parse timezone-aware dates correctly
    },
    # Debugging and logging options - maximized for investigation
    'debug': {
        'verbose_logging': True,  # Enable detailed logging
        'save_raw_html': True,  # Save raw HTML for inspection
        'log_date_extraction': True,  # Log date extraction attempts
        'log_url_patterns': True,  # Log URL pattern matching
        'trace_filtering': True,  # Trace why posts might be filtered out
        'log_selector_attempts': True,  # Log each selector attempt
        'log_metadata_extraction': True,  # Log all metadata extraction
        'capture_screenshots': False,  # Disabled to reduce overhead
        'log_http_headers': True,  # Log HTTP response headers
        'validate_post_structure': True,  # Validate expected post structure
        'log_cache_operations': True,  # NEW: Log all cache hits/misses
        'log_dynamodb_operations': True,  # NEW: Log DynamoDB read/write operations
        'log_url_normalization': True,  # NEW: Log URL normalization steps
        'log_date_parsing_attempts': True,  # NEW: Log every date parsing attempt
        'trace_indexing_pipeline': True,  # NEW: Trace full indexing pipeline
        'dump_extracted_data': True  # NEW: Dump all extracted data for inspection
    },
    # Retry configuration for robustness
    'retry_config': {
        'max_retries': 5,  # Increased from 3 for resilience
        'retry_on_timeout': True,
        'retry_on_http_error': True,
        'retry_on_parse_error': True,
        'retry_on_extraction_failure': True,  # NEW: Retry if data extraction fails
        'retry_on_indexing_failure': True,  # NEW: Retry if DynamoDB write fails
        'backoff_multiplier': 2,
        'initial_retry_delay': 1  # NEW: Start with 1 second delay
    },
    # DynamoDB-specific configuration
    'dynamodb_config': {
        'force_write': True,  # NEW: Force write to DynamoDB even if record exists
        'skip_conditional_writes': True,  # NEW: Skip conditional write checks
        'verify_write_success': True,  # NEW: Verify record was written successfully
        'read_after_write': True,  # NEW: Read back record to confirm
        'overwrite_existing': True,  # NEW: Overwrite existing records unconditionally
        'table_name': 'staging-blog-posts',  # NEW: Explicit table name for verification
        'log_write_operations': True  # NEW: Log all write operations
    },
    # NEW: Post-crawl validation rules
    'validation': {
        'verify_post_indexed': True,  # Verify post appears in index after crawl
        'check_expected_date': EXPECTED_POST_DATE,  # Validate against expected date
        'alert_on_missing': True,  # Alert if post still missing after crawl
        'validate_content_length': True,  # Ensure content was extracted
        'minimum_content_length': 50,  # Reduced from 100 to be more lenient
        'verify_dynamodb_record': True,  # NEW: Explicitly verify DynamoDB record exists
        'check_record_completeness': True,  # NEW: Check all expected fields are populated
        'validate_url_match': True,  # NEW: Ensure crawled URL matches target URL
        'max_validation_retries': 3,  # NEW: Retry validation if it fails
        'validation_delay_seconds': 5  # NEW: Wait before validating to allow indexing
    },
    # Additional metadata for tracking
    'metadata': {
        'trigger_reason': 'Missing blog post investigation - March 2, 2026 post not appearing',
        'post_topic': 'Amazon WorkSpaces Graphics G6 bundles',
        'expected_date': EXPECTED_POST_DATE,
        'investigation_date': datetime.now(timezone.utc).isoformat(),
        'fix_version': '2.2',  # Updated version number
        'primary_fixes': [
            'Disabled date filtering to prevent future date rejection',
            'Enhanced date selector coverage (25+ patterns)',
            'Added date format parsing fallbacks (15+ formats)',
            'Enabled URL discovery cache refresh',
            'Added post-crawl validation',
            'NEW: Added bypass_cache and force_reindex flags',
            'NEW: Enhanced DynamoDB write configuration',
            'NEW: Added fuzzy date parsing',
            'NEW: Increased retry attempts to 5',
            'NEW: Added DynamoDB record verification',
            'NEW: Relaxed content extraction requirements'
        ],
        'investigation_focus': [
            'Date filtering logic',
            'URL pattern matching',
            'DynamoDB table population',
            'Cache invalidation',
            'Date extraction from future-dated posts'
        ]
    }
}

print("Enhanced Crawler Configuration:")
print("=" * 70)
print("✓ Force refresh enabled - will re-crawl even if cached")
print("✓ Bypass cache enabled - ignores all caching layers")
print("✓ Force reindex enabled - will update DynamoDB unconditionally")
print("✓ Date filtering COMPLETELY DISABLED - no date-based filtering")
print("✓ Future dates explicitly accepted (critical for 2026-03-02)")
print("✓ Enhanced date selectors (25+ patterns) for better extraction")
print("✓ Multiple date format parsers (15+ formats) with fallback strategies")
print("✓ Fuzzy date parsing enabled as last resort")
print("✓ URL discovery cache refresh enabled with forced sitemap refresh")
print("✓ Multiple URL patterns configured for better detection")
print("✓ Post-crawl validation enabled with DynamoDB record verification")
print("✓ Verbose logging enabled for comprehensive diagnostics")
print("✓ Date extraction validation without strict requirements")
print("✓ DynamoDB force write enabled to ensure record creation")
print("✓ Retry attempts increased to 5 for maximum resilience")
print("=" * 70)
print()

try:
    req = urllib.request.Request(
        STAGING_API,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'AWS-