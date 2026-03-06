```python
"""
Trigger staging crawler via API with specific URL targeting
Enhanced with date filtering diagnostics and crawler validation
Version 2.5 - Investigation mode for missing blog post detection
Root cause analysis: Why post from March 2, 2026 is not being detected
"""

import json
import urllib.request
import urllib.error
import sys
import time
from datetime import datetime, timezone, timedelta

STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/crawl'

# Specific blog post URL that needs to be crawled
TARGET_BLOG_POST = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'

# Expected publication date of the blog post for validation
EXPECTED_POST_DATE = '2026-03-02'

print("=" * 80)
print("STAGING CRAWLER INVESTIGATION - VERSION 2.5")
print("=" * 80)
print(f"Target: {TARGET_BLOG_POST}")
print(f"Expected Date: {EXPECTED_POST_DATE}")
print(f"Investigation: Why is this post not being detected?")
print(f"Current Time (UTC): {datetime.now(timezone.utc).isoformat()}")
print("=" * 80)
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
        print(f"❌ POTENTIAL ISSUE: Post date is {days_diff} days in the FUTURE")
        print(f"   This may cause crawler rejection if future dates are not accepted")
        print(f"   Investigation Action: Check date filter settings in crawler")
    elif days_diff < -7:
        print(f"❌ POTENTIAL ISSUE: Post date is {abs(days_diff)} days in the PAST")
        print(f"   This may be outside crawler's date range window")
        print(f"   Investigation Action: Check date range configuration")
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
print("   - Is the URL in sitemap?")
print("   - Is the URL accessible (HTTP 200)?")
print("   - Are there URL format validation failures?")
print()
print("2. ❓ Date Filtering Issues:")
print("   - Is future date filtering rejecting the post?")
print("   - Are timezone conversions causing date comparison failures?")
print("   - Is date parsing failing for this specific post?")
print()
print("3. ❓ Content Extraction Issues:")
print("   - Are selectors finding the post content?")
print("   - Is metadata extraction failing?")
print("   - Are required fields missing?")
print()
print("4. ❓ Storage/Indexing Issues:")
print("   - Is DynamoDB write succeeding?")
print("   - Is validation query finding the post?")
print("   - Are there table consistency issues?")
print()
print("5. ❓ Pattern Matching Issues:")
print("   - Do include patterns match the URL?")
print("   - Are exclude patterns blocking the URL?")
print("-" * 80)
print()

# Investigation payload with comprehensive logging and minimal filtering
payload = {
    # Target configuration - force processing
    'target_urls': [TARGET_BLOG_POST],
    'force_refresh': True,
    'bypass_cache': True,
    'force_reindex': True,
    'crawl_depth': 1,
    'ignore_robots_txt': False,  # Check if robots.txt is blocking
    'user_agent': 'AWS-BlogCrawler-Investigation/2.5',
    
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
    
    # Investigation: Completely disable date filtering to eliminate as cause
    'date_filters': {
        'enabled': False,  # PRIMARY FIX: Disable all date filtering
        'start_date': None,
        'end_date': None,
        'ignore_missing_dates': True,
        'accept_future_dates': True,
        'accept_past_dates': True,
        'fallback_to_crawl_date': False,
        'max_future_days': 3650,
        'max_past_days': 3650,
        'validate_date_reasonableness': False,
        'reject_on_date_parsing_failure': False,
        'log_rejection_reasons': True,
        'log_all_date_operations': True,  # Investigation logging
        'timezone_handling': 'utc',
        'allow_timezone_mismatch': True,
        'log_date_filter_decisions': True,  # Log why dates pass/fail
        'trace_date_comparison': True  # Detailed date comparison trace
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
        'log_sitemap_contents': True,  # Investigation: Log entire sitemap
        'log_url_accessibility_details': True,  # Log HTTP response details
        'trace_url_normalization': True,  # Track URL transformations
        'check_robots_txt': True,  # Verify robots.txt allows crawling
        'log_robots_txt_rules': True,  # Log robots.txt content
        'verify_dns_resolution': True,  # Check DNS issues
        'log_http_redirects': True  # Track redirect chains
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
        'extract_all_meta_tags': True,  # Investigation: Get all meta tags
        
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
        'require_date': False,
        'require_title': False,
        'require_content': False,
        'require_author': False,
        'allow_partial_extraction': True,  # Accept partial data
        
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
        'save_parsing_failures': True,  # Investigation: Save failed extractions
        'dump_page_source': True,  # Investigation: Save raw HTML
        'log_selector_matches': True,  # Log which selectors work
        'trace_extraction_pipeline': True  # Full extraction trace
    },
    
    # Investigation: Maximum debugging enabled
    'debug': {
        'verbose_logging': True,
        'save_raw_html': True,
        'log_date_extraction': True,
        'log_url_patterns': True,
        'trace_filtering': True,
        'log_selector_attempts': True,
        'log_metadata_extraction': True,
        'log_http_headers': True,
        'log_cache_operations': True,
        'log_dynamodb_operations': True,
        'log_url_normalization': True,
        'log_date_parsing_attempts': True,
        'trace_indexing_pipeline': True,
        'dump_extracted_data': True,
        'log_every_selector_result': True,
        'log_decision_points': True,
        'trace_data_flow': True,
        'log_storage_operations': True,
        'export_diagnostic_report': True,
        'log_date_comparison_logic': True,
        'log_date_timezone_conversions': True,
        'log_rejection_reasons': True,  # Investigation: Why was post rejected?
        'log_acceptance_reasons': True,  # Investigation: Why was post accepted?
        'trace_crawler_execution': True,  # Full execution trace
        'log_crawler_state': True,  # Log crawler state at each step
        'capture_exception_details': True,  # Full exception stack traces
        'log_http_response_body': True,  # Log response content
        'save_intermediate_results': True,  # Save results at each stage
        'enable_profiling': True,  # Performance profiling
        'log_to_cloudwatch': True,  # Ensure CloudWatch logging
        'create_investigation_report': True  # Generate investigation summary
    },
    
    # Investigation: Aggressive retry configuration
    'retry_config': {
        'max_retries': 5,
        'retry_on_timeout': True,
        'retry_on_http_error': True,
        'retry_on_parse_error': True,
        'retry_on_extraction_failure': True,
        'retry_on_indexing_failure': True,
        'retry_on_date_parsing_failure': True,
        'retry_on_any_error': True,  # Investigation: Retry on any error
        'backoff_multiplier': 2,
        'initial_retry_delay': 2,
        'max_retry_delay': 30,
        'log_retry_attempts': True,
        'log_retry_reasons': True  # Investigation: Why are we retrying?
    },
    
    # Investigation: Enhanced DynamoDB storage
    'dynamodb_config': {
        'force_write': True,
        'skip_conditional_writes': True,
        'verify_write_success': True,
        'read_after_write': True,
        'read_after_write_delay': 3,
        'overwrite_existing': True,
        'table_name': 'staging-blog-posts',
        'log_write_operations': True,
        'trace_write_failures': True,
        'verify_table_exists': True,
        'log_item_structure': True,
        'validate_required_fields': False,
        'capture_write_errors': True,
        'use_consistent_reads': True,
        'convert_dates_to_iso8601': True,
        'store_raw_date_string': True,
        'add_indexing_timestamp': True,
        'add_investigation_metadata': True,  # Investigation: Tag this crawl
        'log_table_capacity': True,  # Check for throttling
        'log_write_latency': True,  # Measure write performance
        'verify_item_retrievable': True  # Verify item can be querie