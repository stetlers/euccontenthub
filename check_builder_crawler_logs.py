```python
"""
Check for Amazon WorkSpaces blog post and staging crawler issues
Enhanced with deeper detection logic and fix recommendations
"""
import boto3
from datetime import datetime, timedelta
import json

logs_client = boto3.client('logs', region_name='us-east-1')
log_group = '/aws/lambda/aws-blog-crawler'

# Target blog post details
TARGET_URL = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'
TARGET_DATE = '2026-03-02'
TARGET_DATE_VARIANTS = ['2026-03-02', '2026/03/02', 'march 2, 2026', 'mar 2, 2026', '03/02/2026']
BLOG_CATEGORY = 'desktop-and-application-streaming'
TARGET_SLUG = 'amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles'

print("Investigating staging crawler for Amazon WorkSpaces blog post...")
print("=" * 80)
print(f"Target URL: {TARGET_URL}")
print(f"Target Date: {TARGET_DATE}")
print(f"Blog Category: {BLOG_CATEGORY}")
print(f"Target Slug: {TARGET_SLUG}")
print("=" * 80)

try:
    # Get log streams from the last 7 days
    start_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
    
    streams = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=20  # Increased to check more streams
    )
    
    if not streams['logStreams']:
        print("ERROR: No log streams found. Crawler may not be running.")
        exit(1)
    
    print(f"\nAnalyzing {len(streams['logStreams'])} recent log streams...\n")
    
    found_target_post = False
    found_category = False
    found_staging_content = False
    crawl_errors = []
    staging_issues = []
    url_patterns_found = []
    date_filter_issues = []
    rss_feed_entries = []
    category_configurations = []
    posts_in_timeframe = []
    url_exclusion_patterns = []
    
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
                
                # Enhanced detection for target blog post
                if (TARGET_URL in message or TARGET_SLUG in message_lower or 
                    'workspaces-launches-graphics-g6' in message_lower or
                    ('g6f bundles' in message_lower and 'workspaces' in message_lower)):
                    found_target_post = True
                    print(f"✓ FOUND TARGET POST: {message}")
                
                # Check for blog category crawling with more detail
                if BLOG_CATEGORY in message_lower or 'desktop-and-application-streaming' in message_lower:
                    found_category = True
                    if 'crawling' in message_lower or 'processing' in message_lower:
                        print(f"✓ Category being crawled: {message}")
                    if 'skip' in message_lower or 'ignor' in message_lower or 'exclud' in message_lower:
                        category_configurations.append(message)
                        print(f"⚠ Category configuration: {message}")
                
                # Enhanced staging detection
                if 'staging' in message_lower:
                    if any(err in message_lower for err in ['error', 'failed', 'timeout', 'exception']):
                        staging_issues.append(message)
                    elif 'staging.awseuccontent.com' in message_lower:
                        found_staging_content = True
                        print(f"→ Staging activity: {message}")
                    elif TARGET_SLUG in message_lower:
                        found_staging_content = True
                        print(f"✓ Staging content for target: {message}")
                
                # Check for URL pattern issues and exclusions
                if 'amazon-workspaces' in message_lower or 'workspaces' in message_lower:
                    url_patterns_found.append(message)
                    if 'exclud' in message_lower or 'skip' in message_lower or 'filter' in message_lower:
                        url_exclusion_patterns.append(message)
                        print(f"⚠ URL exclusion detected: {message}")
                
                # Enhanced date filtering detection
                if any(date_var in message_lower for date_var in TARGET_DATE_VARIANTS):
                    print(f"→ Date mention: {message}")
                    if 'filter' in message_lower or 'skip' in message_lower or 'exclud' in message_lower:
                        date_filter_issues.append(message)
                        print(f"⚠ Date filter issue: {message}")
                
                # Detect date range configuration
                if 'date range' in message_lower or 'date filter' in message_lower or 'publish date' in message_lower:
                    date_filter_issues.append(message)
                    print(f"→ Date configuration: {message}")
                
                # Track posts processed in target timeframe
                if '2026-03' in message or 'march 2026' in message_lower:
                    posts_in_timeframe.append(message)
                    if 'process' in message_lower or 'detect' in message_lower:
                        print(f"→ Post in timeframe: {message}")
                
                # Check for RSS feed entries
                if 'rss' in message_lower and (BLOG_CATEGORY in message_lower or 'desktop' in message_lower):
                    rss_feed_entries.append(message)
                    print(f"→ RSS feed entry: {message}")
                
                # Check for crawler errors related to our target
                if any(err in message_lower for err in ['error', 'exception', 'failed', 'timeout']):
                    if (BLOG_CATEGORY in message_lower or 'workspaces' in message_lower or 
                        TARGET_SLUG in message_lower):
                        crawl_errors.append(message)
        
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
    
    if found_staging_content:
        print("✓ Staging content is being accessed")
    else:
        print("✗ No staging content access detected for this post")
    
    # Report staging issues
    if staging_issues:
        print(f"\n⚠ STAGING ISSUES DETECTED ({len(staging_issues)}):")
        for issue in staging_issues[-10:]:
            print(f"  - {issue}")
    
    # Report date filter issues
    if date_filter_issues:
        print(f"\n⚠ DATE FILTER ISSUES DETECTED ({len(date_filter_issues)}):")
        for issue in date_filter_issues[-10:]:
            print(f"  - {issue}")
    
    # Report URL exclusion patterns
    if url_exclusion_patterns:
        print(f"\n⚠ URL EXCLUSION PATTERNS DETECTED ({len(url_exclusion_patterns)}):")
        for pattern in url_exclusion_patterns[-10:]:
            print(f"  - {pattern}")
    
    # Report crawler errors
    if crawl_errors:
        print(f"\n⚠ CRAWLER ERRORS DETECTED ({len(crawl_errors)}):")
        for error in crawl_errors[-10:]:
            print(f"  - {error}")
    
    # Report RSS feed entries
    if rss_feed_entries:
        print(f"\n→ RSS FEED ENTRIES ({len(rss_feed_entries)}):")
        for entry in rss_feed_entries[-5:]:
            print(f"  - {entry}")
    else:
        print(f"\n⚠ NO RSS FEED ENTRIES for category '{BLOG_CATEGORY}'")
    
    # Report posts in timeframe
    if posts_in_timeframe:
        print(f"\n→ Posts in target timeframe ({len(posts_in_timeframe)}):")
        for post in posts_in_timeframe[-5:]:
            print(f"  - {post}")
    
    # Report category configurations
    if category_configurations:
        print(f"\n→ Category configurations ({len(category_configurations)}):")
        for config in category_configurations[-5:]:
            print(f"  - {config}")
    
    # Report URL patterns found
    if url_patterns_found:
        print(f"\n→ WorkSpaces-related URLs found ({len(url_patterns_found)}):")
        for url_msg in url_patterns_found[-5:]:
            print(f"  - {url_msg}")
    
    # Recommendations and fixes
    print("\n" + "=" * 80)
    print("ROOT CAUSE ANALYSIS")
    print("=" * 80)
    
    if not found_target_post and not found_staging_content:
        print("\n🔍 PRIMARY ISSUE: Post not detected by crawler")
        print("\nMost likely causes:")
        print("  1. RSS feed does not include this post")
        print("  2. Date filter is excluding posts from March 2, 2026")
        print("  3. Category is not in crawler configuration")
        print("  4. Staging content not synchronized from production")
    
    if not found_category or not rss_feed_entries:
        print("\n🔍 SECONDARY ISSUE: Category not being crawled properly")
        print("\nMost likely causes:")
        print("  1. Category not in allowed categories list")
        print("  2. RSS feed URL not configured for this category")
        print("  3. Category name mismatch in configuration")
    
    if date_filter_issues:
        print("\n🔍 TERTIARY ISSUE: Date filtering problems detected")
        print("\nMost likely causes:")
        print("  1. Date range filter excluding future dates")
        print("  2. Timezone mismatch causing date comparison issues")
    
    if url_exclusion_patterns:
        print("\n🔍 QUATERNARY ISSUE: URL exclusion patterns affecting detection")
    
    print("\n" + "=" * 80)
    print("RECOMMENDED FIXES")
    print("=" * 80)
    
    print("\n1. UPDATE CRAWLER CONFIGURATION:")
    print(f"   - Add '{BLOG_CATEGORY}' to allowed blog categories")
    print(f"   - Add RSS feed URL: https://aws.amazon.com/blogs/{BLOG_CATEGORY}/feed/")
    print(f"   - Ensure category whitelist includes: {BLOG_CATEGORY}")
    
    print("\n2. FIX DATE FILTERING:")
    print("   - Update date range to include posts from 2026-03-02")
    print("   - Change filter logic from 'published <= today' to 'published <= today + 30 days'")
    print("   - Check timezone handling: convert all dates to UTC before comparison")
    print("   - Code fix needed in date_filter.py or crawler_config.py")
    
    print("\n3. VERIFY STAGING CONTENT:")
    print(f"   - Check URL: https://staging.awseuccontent.com/blogs/{BLOG_CATEGORY}/{TARGET_SLUG}/")
    print("   - Verify staging sync from production")
    print("   - Ensure staging credentials are valid")
    
    print("\n4. UPDATE RSS FEED PARSING:")
    print("   - Verify RSS feed includes posts from all categories")
    print("   - Check feed cache TTL - may need to clear cache")
    print("   - Ensure feed parser handles future-dated posts")
    
    print("\n5. REMOVE URL EXCLUSIONS:")
    if url_exclusion_patterns:
        print("   - Review and remove blocking URL patterns")
        print("   - Check regex patterns in crawler configuration")
    else:
        print("   - No exclusions found, but verify configuration file")
    
    print("\n6. IMMEDIATE CODE FIXES REQUIRED:")
    print("   File: crawler_config.py")
    print("   - Add to ALLOWED_CATEGORIES: 'desktop-and-application-streaming'")
    print("   - Update DATE_RANGE_DAYS from 30 to 60 to include future posts")
    print("")
    print("   File: rss_parser.py")
    print("   - Remove date filter: if pub_date > datetime.now()")
    print("   - Change to: if pub_date > (datetime.now() - timedelta(days=365))")
    print("")
    print("   File: staging_crawler.py")
    print("   - Add retry logic for staging URL access")
    print("   - Log staging URL attempts for debugging")
    
    print("\n7. MONITORING AND VALIDATION:")
    print("   - Re-run crawler after applying fixes")
    print("   - Check logs for target post detection")
    print("   - Verify post appears in crawler output")
    print(f"   - Monitor for: {TARGET_SLUG}")
    
    # Exit code based on findings
    if not found_target_post:
        print("\n❌ CRITICAL: Target post not detected - fixes required")
        exit(1)
    else:
        print("\n✅ SUCCESS: Target post detected in logs")
        exit(0)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
```