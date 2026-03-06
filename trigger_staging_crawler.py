```python
"""
Trigger staging crawler via API with specific URL targeting
Enhanced with date filtering diagnostics and crawler validation
Version 2.3 - Comprehensive investigation for March 2, 2026 post detection failure
Root cause analysis focus: crawler logic, URL filtering, date parsing, storage mechanisms
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
print("STAGING CRAWLER INVESTIGATION - ROOT CAUSE ANALYSIS")
print("=" * 80)
print(f"Target: {TARGET_BLOG_POST}")
print(f"Expected Date: {EXPECTED_POST_DATE}")
print(f"Investigation Version: 2.3")
print(f"Current Time (UTC): {datetime.now(timezone.utc).isoformat()}")
print("=" * 80)
print()

# Parse expected date to validate it's in the future
try:
    expected_dt = datetime.strptime(EXPECTED_POST_DATE, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    current_dt = datetime.now(timezone.utc)
    days_diff = (expected_dt - current_dt).days
    
    print("DATE VALIDATION:")
    print("-" * 80)
    if days_diff > 0:
        print(f"⚠️  Expected post date is {days_diff} days in the FUTURE")
        print(f"   Root cause hypothesis: Future date rejection in crawler logic")
    elif days_diff < -30:
        print(f"⚠️  Expected post date is {abs(days_diff)} days in the PAST")
        print(f"   Root cause hypothesis: Date range filter excluding old posts")
    else:
        print(f"✓  Expected post date is within normal range ({days_diff} days difference)")
    print("-" * 80)
    print()
except Exception as e:
    print(f"⚠️  WARNING: Could not parse expected date: {e}")
    print(f"   Root cause hypothesis: Date parsing logic may have similar issues")
    print()

# Prepare comprehensive payload for root cause investigation
# Addresses all potential failure points: URL filtering, date parsing, caching, storage
payload = {
    # Target configuration
    'target_urls': [TARGET_BLOG_POST],
    'force_refresh': True,
    'bypass_cache': True,
    'force_reindex': True,
    'crawl_depth': 1,
    
    # URL pattern matching - investigation of URL filtering logic
    'include_patterns': [
        '/blogs/desktop-and-application-streaming/*',
        '/blogs/*/amazon-workspaces-*',
        '*/amazon-workspaces-launches-*',
        '*amazon-workspaces-launches-graphics-g6*',  # Most specific pattern
        '/blogs/desktop-and-application-streaming/amazon-workspaces-launches-*'
    ],
    'exclude_patterns': [],  # Explicitly empty to ensure no exclusions
    
    # CRITICAL: Date filtering completely disabled for root cause analysis
    # This isolates whether date filtering is the root cause
    'date_filters': {
        'enabled': False,
        'start_date': None,
        'end_date': None,
        'ignore_missing_dates': True,
        'accept_future_dates': True,
        'accept_past_dates': True,
        'fallback_to_crawl_date': False,
        'max_future_days': 3650,
        'validate_date_reasonableness': False,
        'log_rejection_reasons': True  # NEW: Log why dates might be rejected
    },
    
    # URL discovery configuration - investigation of URL detection logic
    'url_detection': {
        'check_sitemap': True,
        'check_rss': True,
        'follow_canonical': True,
        'validate_links': True,
        'check_sitemap_index': True,
        'parse_atom_feeds': True,
        'refresh_discovery_cache': True,
        'force_sitemap_refresh': True,
        'check_blog_index_pages': True,
        'follow_pagination': True,
        'max_discovery_depth': 3,
        'verify_url_accessibility': True,  # NEW: Verify URL is accessible before crawling
        'log_discovery_process': True,  # NEW: Log entire discovery process
        'check_url_redirects': True,  # NEW: Follow and log redirects
        'validate_url_format': True  # NEW: Log URL format validation
    },
    
    # Scraping configuration - investigation of date parsing logic
    'scraping_config': {
        'extract_metadata': True,
        'parse_json_ld': True,
        'extract_og_tags': True,
        'extract_article_schema': True,
        'extract_dublin_core': True,
        'extract_twitter_cards': True,
        'parse_microdata': True,
        'parse_rdfa': True,
        
        # Comprehensive selectors for root cause analysis
        'selectors': {
            'title': [
                'h1.blog-post-title',
                'h1.entry-title',
                'h1',
                'article h1',
                '.post-title',
                'meta[property="og:title"]',
                'meta[name="twitter:title"]',
                'meta[name="title"]',
                '[itemprop="headline"]',
                '.page-title',
                '#post-title'
            ],
            # ENHANCED: Exhaustive date selector list for parsing investigation
            'date': [
                'meta[property="article:published_time"]',
                'meta[property="article:published"]',
                'meta[name="publish-date"]',
                'meta[name="publishdate"]',
                'meta[name="publication-date"]',
                'meta[name="date"]',
                'meta[name="DC.date"]',
                'meta[name="DC.date.issued"]',
                'meta[name="DC.date.created"]',
                'meta[name="dcterms.created"]',
                'meta[property="article:modified_time"]',
                'meta[name="last-modified"]',
                'time[datetime]',
                'time[pubdate]',
                'time.published',
                'time.entry-date',
                'time.updated',
                '.post-date',
                '.published-date',
                '.entry-date',
                '.publication-date',
                'span.date',
                'div.date',
                '.blog-post-meta time',
                '.blog-post-date',
                '.blog-post-metadata time',
                '.aws-blog-date',
                '.post-meta time',
                '[itemprop="datePublished"]',
                '[itemprop="dateCreated"]',
                'script[type="application/ld+json"]',
                '.timestamp',
                '#post-date',
                '[data-date]',
                '[datetime]'
            ],
            'content': [
                'article',
                '.post-content',
                '.blog-post-content',
                '.entry-content',
                'main',
                '.main-content',
                '[itemprop="articleBody"]',
                '.aws-blog-content',
                '#content',
                '.content-body'
            ],
            'author': [
                '.author',
                '.post-author',
                '.entry-author',
                '.blog-author',
                'meta[name="author"]',
                'meta[property="article:author"]',
                '[itemprop="author"]',
                '[rel="author"]',
                '.byline'
            ]
        },
        
        # Relaxed requirements to capture data even with parsing failures
        'require_date': False,
        'require_title': False,
        'require_content': False,
        
        # Comprehensive date format coverage for parsing investigation
        'date_formats': [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%B %d, %Y',  # March 2, 2026
            '%b %d, %Y',
            '%d %B %Y',
            '%d %b %Y',
            '%Y/%m/%d',
            '%m/%d/%Y',
            '%d-%m-%Y',
            '%d.%m.%Y',
            '%Y.%m.%d',
            'iso8601',
            'rfc3339',
            'rfc2822'
        ],
        
        # All fallback mechanisms enabled for parsing investigation
        'date_parsing_fallbacks': True,
        'extract_dates_from_url': True,
        'use_fuzzy_date_parsing': True,
        'parse_relative_dates': True,
        'timezone_aware': True,
        'try_multiple_parsers': True,  # NEW: Try all available date parsers
        'log_all_parsing_attempts': True  # NEW: Log every single parsing attempt
    },
    
    # MAXIMUM debugging for comprehensive investigation
    'debug': {
        'verbose_logging': True,
        'save_raw_html': True,
        'log_date_extraction': True,
        'log_url_patterns': True,
        'trace_filtering': True,
        'log_selector_attempts': True,
        'log_metadata_extraction': True,
        'capture_screenshots': False,
        'log_http_headers': True,
        'validate_post_structure': True,
        'log_cache_operations': True,
        'log_dynamodb_operations': True,
        'log_url_normalization': True,
        'log_date_parsing_attempts': True,
        'trace_indexing_pipeline': True,
        'dump_extracted_data': True,
        'log_every_selector_result': True,  # NEW: Log result of each selector
        'log_decision_points': True,  # NEW: Log every decision point in crawler
        'trace_data_flow': True,  # NEW: Trace data through entire pipeline
        'log_storage_operations': True,  # NEW: Log all storage mechanism operations
        'export_diagnostic_report': True  # NEW: Export full diagnostic report
    },
    
    # Enhanced retry configuration for resilience
    'retry_config': {
        'max_retries': 5,
        'retry_on_timeout': True,
        'retry_on_http_error': True,
        'retry_on_parse_error': True,
        'retry_on_extraction_failure': True,
        'retry_on_indexing_failure': True,
        'backoff_multiplier': 2,
        'initial_retry_delay': 1,
        'log_retry_attempts': True  # NEW: Log each retry with reason
    },
    
    # DynamoDB storage mechanism investigation
    'dynamodb_config': {
        'force_write': True,
        'skip_conditional_writes': True,
        'verify_write_success': True,
        'read_after_write': True,
        'overwrite_existing': True,
        'table_name': 'staging-blog-posts',
        'log_write_operations': True,
        'trace_write_failures': True,  # NEW: Detailed trace of any write failures
        'verify_table_exists': True,  # NEW: Verify table exists before writing
        'log_item_structure': True,  # NEW: Log structure of item being written
        'validate_required_fields': False,  # NEW: Don't fail on missing fields
        'capture_write_errors': True  # NEW: Capture and log all write errors
    },
    
    # Post-crawl validation for storage mechanism verification
    'validation': {
        'verify_post_indexed': True,
        'check_expected_date': EXPECTED_POST_DATE,
        'alert_on_missing': True,
        'validate_content_length': True,
        'minimum_content_length': 50,
        'verify_dynamodb_record': True,
        'check_record_completeness': True,
        'validate_url_match': True,
        'max_validation_retries': 3,
        'validation_delay_seconds': 5,
        'query_by_date': True,  # NEW: Try to query by expected date
        'query_by_url': True,  # NEW: Try to query by URL
        'query_by_title_keywords': True,  # NEW: Try to query by title keywords
        'log_validation_queries': True  # NEW: Log all validation queries
    },
    
    # Investigation metadata for tracking
    'metadata': {
        'trigger_reason': 'ROOT CAUSE INVESTIGATION: March 2, 2026 post not detected',
        'post_topic': 'Amazon WorkSpaces Graphics G6, Gr6, and G6f bundles',
        'expected_date': EXPECTED_POST_DATE,
        'investigation_date': datetime.now(timezone.utc).isoformat(),
        'fix_version': '2.3',
        'investigation_areas': [
            'Crawler logic - URL pattern matching and filtering',
            'URL filtering - Include/exclude pattern effectiveness',
            'Date parsing - Future date handling and format support',
            'Storage mechanisms - DynamoDB write operations and verification',
            'Cache invalidation - Bypass mechanisms and effectiveness',
            'Discovery process - Sitemap and RSS feed parsing'
        ],
        'diagnostic_features': [
            'Complete date filtering bypass',
            'Exhaustive date selector coverage (30+ patterns)',
            'Comprehensive date format support (18+ formats)',
            'DynamoDB write verification with read-after-write',
            'Full pipeline tracing from URL to storage',
            'Multi-layer validation with multiple query strategies',
            'Maximum debug logging at every decision point',
            'Raw HTML capture for offline analysis'
        ],
        'expected_outcomes': [
            'Identify if URL is being discovered but filtered',
            'Determine if date parsing is failing or rejecting future dates',
            'Verify if DynamoDB writes are succeeding but queries failing',
            'Confirm if cache is preventing re-indexing',
            'Isolate exact failure point in crawler pipeline'
        ]
    }
}

print("ROOT CAUSE INVESTIGATION CONFIGURATION:")
print("=" * 80)
print("\n[URL FILTERING INVESTIGATION]")
print("  ✓ 5 specific URL patterns configured")
print("  ✓ No exclusion patterns (isolation test)")
print("  ✓ URL accessibility verification enabled")
print("  ✓ Redirect following and logging enabled")

print("\n[DATE PARSING INVESTIGATION]")
print("  ✓ Date filtering COMPLETELY DISABLED (isolation test)")
print("  ✓ 30+ date selector patterns configured")
print("  ✓ 18+ date format parsers configured")
print("  ✓ Future dates explicitly accepted (critical for 2026-03-02)")
print("  ✓ Fuzzy parsing enabled as fallback")
print("  ✓ All parsing attempts logged individually")

print("\n[STORAGE MECHANISM INVESTIGATION]")
print("  ✓ Force write to DynamoDB enabled")
print("  ✓ Conditional write checks bypassed")
print("  ✓ Read-after-write verification enabled")
print("  ✓ Write operation logging enabled")
print("  ✓ Table existence verification enabled")

print("\n[CRAWLER LOGIC INVESTIGATION]")
print("  ✓ Full pipeline tracing enabled")
print("  ✓ Every decision point logged")
print("  ✓ Selector results logged individually")
print("  ✓ Data flow traced end-to-end")
print("  ✓ Raw HTML saved for offline analysis")

print("\n[VALIDATION & VERIFICATION]")
print("  ✓ Post-crawl validation