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
TARGET_DATE_VARIATIONS = ['2026-03-02', '2026/03/02', 'march 2, 2026', 'march 2nd, 2026', '03/02/2026', '03-02-2026']
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
                
                # Enhanced URL detection analysis
                if any(keyword in message_lower for keyword in ['url detected', 'url found', 'discovering url', 'url pattern', 'url match']):
                    url_detection_info.append(message)
                    if 'workspaces' in message_lower or BLOG_CATEGORY in message_lower:
                        print(f"→ URL detection: {message}")
                
                # Enhanced scraping pattern analysis
                if any(keyword in message_lower for keyword in ['scraping', 'parsing', 'extracting', 'html pattern', 'css selector', 'xpath']):
                    scraping_pattern_info.append(message)
                    if 'workspaces' in message_lower or BLOG_CATEGORY in message_lower:
                        print(f"→ Scraping pattern: {message}")
                
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
                
                # Check for skipped or filtered posts
                if any(keyword in message_lower for keyword in ['skipped', 'filtered', 'excluded', 'ignored', 'not processing']):
                    if 'workspaces' in message_lower or BLOG_CATEGORY in message_lower or any(date_var in message_lower for date_var in [d.lower() for d in TARGET_DATE_VARIATIONS]):
                        print(f"⚠ Post may be filtered: {message}")
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
    
    # Report URL detection analysis
    if url_detection_info:
        print(f"\n→ URL DETECTION ANALYSIS ({len(url_detection_info)} entries):")
        for info in url_detection_info[-15:]:  # Last 15 entries
            print(f"  - {info}")
    else:
        print("\n⚠ NO URL DETECTION INFO FOUND - May indicate missing URL detection logging")
    
    # Report scraping pattern analysis
    if scraping_pattern_info:
        print(f"\n→ SCRAPING PATTERN ANALYSIS ({len(scraping_pattern_info)} entries):")
        for info in scraping_pattern_info[-15:]:  # Last 15 entries
            print(f"  - {info}")
    else:
        print("\n⚠ NO SCRAPING PATTERN INFO FOUND - May indicate missing scraping logging")
    
    # Report RSS feed analysis
    if rss_feed_entries:
        print(f"\n→ RSS FEED ANALYSIS ({len(rss_feed_entries)} entries):")
        for entry in rss_feed_entries[-10:]:  # Last 10 entries
            print(f"  - {entry}")
    else:
        print("\n⚠ NO RSS FEED ENTRIES FOUND - RSS may not be processing this category")
    
    # Report date range configuration
    if date_range_configs:
        print(f"\n→ DATE RANGE CONFIGURATION ({len(date_range_configs)} entries):")
        for config in date_range_configs[-10:]:  # Last 10 entries
            print(f"  - {config}")
    else:
        print("\n⚠ NO DATE RANGE CONFIG FOUND - May use default settings")
    
    # Report staging issues
    if staging_issues:
        print(f"\n⚠ STAGING ISSUES DETECTED ({len(staging_issues)}):")
        for issue in staging_issues[-10:]:  # Last 10 issues
            print(f"  - {issue}")
    
    # Report crawler errors
    if crawl_errors:
        print(f"\n⚠ CRAWLER ERRORS DETECTED ({len(crawl_errors)}):")
        for error in crawl_errors[-10:]:  # Last 10 errors
            print(f"  - {error}")
    
    # Report URL patterns found
    if url_patterns_found:
        print(f"\n→ WorkSpaces-related URLs found ({len(url_patterns_found)}):")
        for url_msg in url_patterns_found[-5:]:  # Last 5
            print(f"  - {url_msg}")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    if not found_target_post:
        print("PRIMARY ISSUES TO INVESTIGATE:")
        print("1. Verify the blog post exists and is accessible at the URL")
        print("   - Check: curl -I " + TARGET_URL)
        print("   - Verify publish date is March 2, 2026")
        
        if not date_filter_info:
            print("\n2. DATE FILTERING ISSUE (CRITICAL):")
            print("   - No date filter logs found - crawler may not be checking dates correctly")
            print("   - Check crawler's date extraction logic from blog posts")
            print("   - Verify date parsing handles format: 'March 2, 2026'")
            print("   - Add logging to date filtering logic")
        else:
            print("\n2. DATE FILTERING:")
            print("   - Review date filter logs above for cutoff dates")
            print("   - Ensure date range includes March 2, 2026")
            print("   - Check if crawler has a 'max age' setting that excludes this date")
        
        if not url_detection_info:
            print("\n3. URL DETECTION ISSUE (CRITICAL):")
            print("   - No URL detection logs found - crawler may not be discovering new URLs")
            print("   - Check RSS feed parsing for this blog category")
            print("   - Verify sitemap.xml includes the target URL")
            print("   - Add logging to URL discovery logic")
        else:
            print("\n3. URL DETECTION:")
            print("   - Review URL detection logs above")
            print("   - Check if URL pattern matches for 'amazon-workspaces-launches-graphics-g6'")
        
        if not scraping_pattern_info:
            print("\n4. SCRAPING PATTERN ISSUE (CRITICAL):")
            print("   - No scraping pattern logs found - crawler may not be extracting content")
            print("   - Verify HTML structure of target blog post")
            print("   - Check CSS selectors/XPath patterns for blog post elements")
            print("   - Add logging to content extraction logic")
        else:
            print("\n4. SCRAPING PATTERNS:")
            print("   - Review scraping pattern logs above")
            print("   - Test scraping patterns against target URL")
        
        print("\n5. STAGING ENVIRONMENT:")
        print("   - Verify staging.awseuccontent.com has the latest content")
        print("   - Check content synchronization from production")
        print("   - Ensure staging environment is accessible from crawler")
        
        if not rss_feed_entries:
            print("\n6. RSS FEED ISSUE:")
            print("   - No RSS entries found for this category")
            print("   - Check if RSS feed includes 'desktop-and-application-streaming'")
            print("   - Verify RSS feed URL is correct and accessible")
            print("   - Check if RSS feed has entries dated March 2, 2026")
    
    if not found_category:
        print("\n7. BLOG CATEGORY CONFIGURATION:")
        print("   - Add 'desktop-and-application-streaming' to crawler configuration")
        print("   - Verify blog category whitelist/blacklist settings")
        print("   - Check if category URL routing is correct")
    
    if staging_issues:
        print("\n8. STAGING ENVIRONMENT FIXES:")
        print("   - Review staging environment connectivity and authentication")
        print("   - Check staging content synchronization from production")
        print("   - Verify SSL/TLS certificates for staging domain")
    
    if crawl_errors:
        print("\n9. CRAWLER ERROR FIXES:")
        print("   - Review and fix crawler errors for this category")
        print("   - Check rate limiting and timeout configurations")
        print("   - Increase error logging verbosity")
    
    print("\n" + "=" * 80)
    print("IMMEDIATE ACTIONS")
    print("=" * 80)
    print("1. Add enhanced logging to crawler for:")
    print("   - Date filtering logic (log every date comparison)")
    print("   - URL detection (log every URL discovered and filtered)")
    print("   - Scraping patterns (log extraction success/failure)")
    print("2. Run crawler in debug mode for this specific blog category")
    print("3. Manually test the target URL with crawler's scraping logic")
    print("4. Verify date range configuration allows posts from March 2026")
    print("5. Check if crawler has processed any posts from March 2026")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
```