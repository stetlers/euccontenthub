```python
"""
Check for Amazon WorkSpaces blog post and staging crawler issues
Enhanced with detailed date filtering, URL detection, and scraping pattern analysis
"""
import boto3
import json
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')
log_group = '/aws/lambda/aws-blog-crawler'

# Target blog post details
TARGET_URL = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'
TARGET_DATE = '2026-03-02'
TARGET_DATE_VARIATIONS = ['2026-03-02', '2026/03/02', 'march 2, 2026', 'march 2nd, 2026', '03/02/2026', '03-02-2026', 'mar 2, 2026', '2-mar-2026', '2 march 2026']
BLOG_CATEGORY = 'desktop-and-application-streaming'

print("Investigating staging crawler for Amazon WorkSpaces blog post...")
print("=" * 80)
print(f"Target URL: {TARGET_URL}")
print(f"Target Date: {TARGET_DATE}")
print(f"Blog Category: {BLOG_CATEGORY}")
print("=" * 80)

try:
    # Get log streams from the last 14 days (extended to catch more data)
    start_time = int((datetime.now() - timedelta(days=14)).timestamp() * 1000)
    
    streams = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=20  # Increased to analyze more streams
    )
    
    if not streams['logStreams']:
        print("ERROR: No log streams found. Crawler may not be running.")
        exit(1)
    
    print(f"\nAnalyzing {len(streams['logStreams'])} recent log streams...\n")
    
    found_target_post = False
    found_category = False
    crawl_errors = []
    staging_issues = []
    url_patterns_found = []
    date_filter_info = []
    url_detection_info = []
    scraping_pattern_info = []
    rss_feed_entries = []
    date_range_configs = []
    
    # Enhanced tracking for new diagnostics
    date_parsing_errors = []
    url_metadata_issues = []
    blog_post_skipped = []
    date_comparison_logs = []
    feed_parsing_logs = []
    html_structure_logs = []
    content_extraction_logs = []
    post_validation_logs = []
    storage_mechanism_logs = []
    database_insertion_logs = []
    duplicate_check_logs = []
    
    for stream in streams['logStreams']:
        stream_name = stream['logStreamName']
        
        try:
            # Get log events with pagination
            next_token = None
            all_events = []
            
            while True:
                if next_token:
                    response = logs_client.get_log_events(
                        logGroupName=log_group,
                        logStreamName=stream_name,
                        startFromHead=True,
                        nextToken=next_token,
                        limit=10000
                    )
                else:
                    response = logs_client.get_log_events(
                        logGroupName=log_group,
                        logStreamName=stream_name,
                        startFromHead=True,
                        limit=10000
                    )
                
                events = response['events']
                all_events.extend(events)
                
                # Check if we've reached the end
                if 'nextForwardToken' in response and response['nextForwardToken'] != next_token:
                    next_token = response['nextForwardToken']
                else:
                    break
            
            # Analyze events for issues
            for event in all_events:
                message = event['message'].strip()
                message_lower = message.lower()
                
                # Check for target blog post
                if TARGET_URL in message or 'workspaces-launches-graphics-g6' in message_lower:
                    found_target_post = True
                    print(f"✓ FOUND TARGET POST: {message}")
                
                # Check for blog category crawling
                if BLOG_CATEGORY in message_lower or 'desktop-and-application-streaming' in message_lower:
                    found_category = True
                    if 'crawling' in message_lower or 'processing' in message_lower:
                        print(f"✓ Category being crawled: {message}")
                
                # Enhanced date filtering analysis
                if any(keyword in message_lower for keyword in ['date filter', 'date range', 'filtering by date', 'date threshold', 'cutoff date']):
                    date_filter_info.append(message)
                    print(f"→ Date filter detected: {message}")
                
                # Check for any of the target date variations
                if any(date_var in message_lower for date_var in [d.lower() for d in TARGET_DATE_VARIATIONS]):
                    date_filter_info.append(message)
                    print(f"→ Target date mention: {message}")
                
                # Date parsing error detection
                if any(keyword in message_lower for keyword in ['date parse', 'date parsing', 'parse date', 'invalid date', 'date format', 'date conversion']):
                    date_parsing_errors.append(message)
                    if 'error' in message_lower or 'fail' in message_lower:
                        print(f"⚠ Date parsing error: {message}")
                
                # Date comparison logging
                if any(keyword in message_lower for keyword in ['date comparison', 'comparing dates', 'date check', 'date older than', 'date newer than', 'within date range']):
                    date_comparison_logs.append(message)
                    if 'workspaces' in message_lower or '2026-03' in message or 'march 2026' in message_lower:
                        print(f"→ Date comparison: {message}")
                
                # Enhanced URL detection analysis
                if any(keyword in message_lower for keyword in ['url detected', 'url found', 'discovering url', 'url pattern', 'url match', 'discovered url']):
                    url_detection_info.append(message)
                    if 'workspaces' in message_lower or BLOG_CATEGORY in message_lower:
                        print(f"→ URL detection: {message}")
                
                # URL metadata parsing issues
                if any(keyword in message_lower for keyword in ['metadata', 'meta tag', 'og:published', 'article:published', 'pubdate', 'publish date']):
                    url_metadata_issues.append(message)
                    if 'workspaces' in message_lower or 'error' in message_lower or 'missing' in message_lower:
                        print(f"→ Metadata parsing: {message}")
                
                # Enhanced scraping pattern analysis
                if any(keyword in message_lower for keyword in ['scraping', 'parsing', 'extracting', 'html pattern', 'css selector', 'xpath']):
                    scraping_pattern_info.append(message)
                    if 'workspaces' in message_lower or BLOG_CATEGORY in message_lower:
                        print(f"→ Scraping pattern: {message}")
                
                # Feed parsing logs
                if any(keyword in message_lower for keyword in ['feed parsing', 'parsing feed', 'feed entry', 'feed item', 'rss entry', 'atom entry']):
                    feed_parsing_logs.append(message)
                    if BLOG_CATEGORY in message_lower or 'workspaces' in message_lower:
                        print(f"→ Feed parsing: {message}")
                
                # HTML structure analysis
                if any(keyword in message_lower for keyword in ['html structure', 'dom parsing', 'element not found', 'selector failed', 'missing element']):
                    html_structure_logs.append(message)
                    if 'workspaces' in message_lower or BLOG_CATEGORY in message_lower:
                        print(f"→ HTML structure: {message}")
                
                # Content extraction logging
                if any(keyword in message_lower for keyword in ['extracting content', 'content extracted', 'extraction failed', 'title extracted', 'date extracted']):
                    content_extraction_logs.append(message)
                    if 'workspaces' in message_lower or BLOG_CATEGORY in message_lower:
                        print(f"→ Content extraction: {message}")
                
                # Post validation logging
                if any(keyword in message_lower for keyword in ['validating post', 'post validation', 'validation failed', 'validation passed', 'post valid', 'post invalid']):
                    post_validation_logs.append(message)
                    if 'workspaces' in message_lower or BLOG_CATEGORY in message_lower:
                        print(f"→ Post validation: {message}")
                
                # Storage mechanism logging
                if any(keyword in message_lower for keyword in ['storing', 'saving', 'persisting', 'storage', 'write to', 'save to']):
                    storage_mechanism_logs.append(message)
                    if 'workspaces' in message_lower or BLOG_CATEGORY in message_lower or 'staging' in message_lower:
                        print(f"→ Storage mechanism: {message}")
                
                # Database insertion logging
                if any(keyword in message_lower for keyword in ['database insert', 'db insert', 'inserting into', 'insert query', 'dynamodb put', 's3 upload', 'writing to database']):
                    database_insertion_logs.append(message)
                    if 'workspaces' in message_lower or BLOG_CATEGORY in message_lower:
                        print(f"→ Database insertion: {message}")
                
                # Duplicate check logging
                if any(keyword in message_lower for keyword in ['duplicate', 'already exists', 'existing post', 'duplicate check', 'checking for duplicates']):
                    duplicate_check_logs.append(message)
                    if 'workspaces' in message_lower or BLOG_CATEGORY in message_lower:
                        print(f"→ Duplicate check: {message}")
                
                # Check for RSS feed processing
                if 'rss' in message_lower or 'feed' in message_lower:
                    if BLOG_CATEGORY in message_lower or 'workspaces' in message_lower:
                        rss_feed_entries.append(message)
                        print(f"→ RSS feed entry: {message}")
                
                # Check for date range configuration
                if any(keyword in message_lower for keyword in ['date range config', 'max age', 'min date', 'lookback period', 'days back']):
                    date_range_configs.append(message)
                    print(f"→ Date range config: {message}")
                
                # Check for staging-specific issues
                if 'staging' in message_lower:
                    if any(err in message_lower for err in ['error', 'failed', 'timeout', 'exception']):
                        staging_issues.append(message)
                    elif 'staging.awseuccontent.com' in message_lower:
                        print(f"→ Staging activity: {message}")
                
                # Check for URL pattern issues
                if 'amazon-workspaces' in message_lower or 'workspaces' in message_lower:
                    if any(keyword in message_lower for keyword in ['url', 'link', 'href', 'blog post']):
                        url_patterns_found.append(message)
                
                # Check for crawler errors
                if any(err in message_lower for err in ['error', 'exception', 'failed', 'timeout']):
                    if BLOG_CATEGORY in message_lower or 'workspaces' in message_lower:
                        crawl_errors.append(message)
                
                # Enhanced detection for skipped or filtered posts
                if any(keyword in message_lower for keyword in ['skipped', 'filtered', 'excluded', 'ignored', 'not processing', 'rejected', 'skipping']):
                    if 'workspaces' in message_lower or BLOG_CATEGORY in message_lower or any(date_var in message_lower for date_var in [d.lower() for d in TARGET_DATE_VARIATIONS]):
                        blog_post_skipped.append(message)
                        print(f"⚠ Post may be filtered/skipped: {message}")
                        date_filter_info.append(message)
        
        except Exception as stream_error:
            print(f"Warning: Could not process stream {stream_name}: {stream_error}")
            continue
    
    # Report findings
    print("\n" + "=" * 80)
    print("DIAGNOSTIC REPORT")
    print("=" * 80)
    
    if found_target_post:
        print("✓ Target blog post WAS FOUND in logs")
    else:
        print("✗ Target blog post NOT FOUND in logs")
        print("  → The crawler did not detect or process this post")
    
    if found_category:
        print(f"✓ Blog category '{BLOG_CATEGORY}' is being crawled")
    else:
        print(f"✗ Blog category '{BLOG_CATEGORY}' may not be in crawler scope")
    
    # Report date filtering analysis
    if date_filter_info:
        print(f"\n→ DATE FILTERING ANALYSIS ({len(date_filter_info)} entries):")
        for info in date_filter_info[-15:]:  # Last 15 entries
            print(f"  - {info}")
    else:
        print("\n⚠ NO DATE FILTERING INFO FOUND - May indicate missing date filter logging")
    
    # Report date parsing errors
    if date_parsing_errors:
        print(f"\n⚠ DATE PARSING ERRORS DETECTED ({len(date_parsing_errors)} entries):")
        for error in date_parsing_errors[-10:]:
            print(f"  - {error}")
    else:
        print("\n→ No date parsing errors detected")
    
    # Report date comparison logs
    if date_comparison_logs:
        print(f"\n→ DATE COMPARISON LOGS ({len(date_comparison_logs)} entries):")
        for log in date_comparison_logs[-15:]:
            print(f"  - {log}")
    else:
        print("\n⚠ NO DATE COMPARISON LOGS - Date filtering may not be logging comparisons")
    
    # Report URL detection analysis
    if url_detection_info:
        print(f"\n→ URL DETECTION ANALYSIS ({len(url_detection_info)} entries):")
        for info in url_detection_info[-15:]:  # Last 15 entries
            print(f"  - {info}")
    else:
        print("\n⚠ NO URL DETECTION INFO FOUND - May indicate missing URL detection logging")
    
    # Report URL metadata issues
    if url_metadata_issues:
        print(f"\n→ URL METADATA PARSING ({len(url_metadata_issues)} entries):")
        for issue in url_metadata_issues[-10:]:
            print(f"  - {issue}")
    else:
        print("\n⚠ NO URL METADATA LOGS - Metadata extraction may not be logged")
    
    # Report scraping pattern analysis
    if scraping_pattern_info:
        print(f"\n→ SCRAPING PATTERN ANALYSIS ({len(scraping_pattern_info)} entries):")
        for info in scraping_pattern_info[-15:]:  # Last 15 entries
            print(f"  - {info}")
    else:
        print("\n⚠ NO SCRAPING PATTERN INFO FOUND - May indicate missing scraping logging")
    
    # Report feed parsing logs
    if feed_parsing_logs:
        print(f"\n→ FEED PARSING LOGS ({len(feed_parsing_logs)} entries):")
        for log in feed_parsing_logs[-10:]:
            print(f"  - {log}")
    else:
        print("\n⚠ NO FEED PARSING LOGS - Feed processing may not be logged")
    