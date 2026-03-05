```python
"""
Check for Amazon WorkSpaces blog post and staging crawler issues
"""
import boto3
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')
log_group = '/aws/lambda/aws-blog-crawler'

# Target blog post details
TARGET_URL = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'
TARGET_DATE = '2026-03-02'
BLOG_CATEGORY = 'desktop-and-application-streaming'
STAGING_DOMAIN = 'staging.awseuccontent.com'

print("Investigating staging crawler for Amazon WorkSpaces blog post...")
print("=" * 80)
print(f"Target URL: {TARGET_URL}")
print(f"Target Date: {TARGET_DATE}")
print(f"Blog Category: {BLOG_CATEGORY}")
print(f"Staging Domain: {STAGING_DOMAIN}")
print("=" * 80)

try:
    # Get log streams from the last 7 days
    start_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
    
    streams = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=10
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
    staging_domain_mentions = []
    date_filter_issues = []
    future_date_blocks = []
    
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
                
                # Enhanced staging domain detection
                if STAGING_DOMAIN in message_lower or 'staging.aws' in message_lower:
                    staging_domain_mentions.append(message)
                    if any(err in message_lower for err in ['error', 'failed', 'timeout', 'exception', 'unavailable', 'not found', '404', '503', 'connection']):
                        staging_issues.append(message)
                        print(f"✗ Staging error: {message}")
                    elif any(status in message_lower for status in ['success', 'completed', 'fetched', 'crawled']):
                        print(f"→ Staging activity: {message}")
                
                # Check for staging vs production domain confusion
                if 'aws.amazon.com' in message_lower and 'staging' in message_lower:
                    print(f"→ Domain routing: {message}")
                
                # Check for URL pattern issues
                if 'amazon-workspaces' in message_lower or 'workspaces' in message_lower:
                    url_patterns_found.append(message)
                
                # Enhanced date filtering detection
                if TARGET_DATE in message or 'march 2, 2026' in message_lower or '2026-03-02' in message:
                    print(f"→ Date mention: {message}")
                    if any(term in message_lower for term in ['skip', 'filter', 'exclude', 'ignore', 'future']):
                        date_filter_issues.append(message)
                
                # Check for future date blocking (common issue for dates ahead of current time)
                if any(term in message_lower for term in ['future date', 'date is ahead', 'post date exceeds', 'date validation failed', 'invalid date']):
                    if '2026' in message:
                        future_date_blocks.append(message)
                        print(f"⚠ Future date filter detected: {message}")
                
                # Check for crawler errors
                if any(err in message_lower for err in ['error', 'exception', 'failed', 'timeout']):
                    if BLOG_CATEGORY in message_lower or 'workspaces' in message_lower:
                        crawl_errors.append(message)
                
                # Check for staging-specific configuration issues
                if 'config' in message_lower and 'staging' in message_lower:
                    print(f"→ Staging config: {message}")
                
                # Check for RSS feed issues with staging
                if 'rss' in message_lower or 'feed' in message_lower:
                    if BLOG_CATEGORY in message_lower or 'staging' in message_lower:
                        print(f"→ Feed activity: {message}")
        
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
    
    # Report staging domain interactions
    if staging_domain_mentions:
        print(f"\n→ STAGING DOMAIN MENTIONS ({len(staging_domain_mentions)}):")
        for mention in staging_domain_mentions[-10:]:
            print(f"  - {mention}")
    else:
        print(f"\n✗ NO STAGING DOMAIN MENTIONS FOUND")
        print(f"  → Crawler may not be configured to use {STAGING_DOMAIN}")
    
    # Report staging issues
    if staging_issues:
        print(f"\n⚠ STAGING ISSUES DETECTED ({len(staging_issues)}):")
        for issue in staging_issues[-10:]:
            print(f"  - {issue}")
    
    # Report future date blocking
    if future_date_blocks:
        print(f"\n⚠ FUTURE DATE FILTERING DETECTED ({len(future_date_blocks)}):")
        for block in future_date_blocks:
            print(f"  - {block}")
        print("  → POST DATE (2026-03-02) MAY BE BLOCKED AS FUTURE DATE")
    
    # Report date filter issues
    if date_filter_issues:
        print(f"\n⚠ DATE FILTER ISSUES ({len(date_filter_issues)}):")
        for issue in date_filter_issues:
            print(f"  - {issue}")
    
    # Report crawler errors
    if crawl_errors:
        print(f"\n⚠ CRAWLER ERRORS DETECTED ({len(crawl_errors)}):")
        for error in crawl_errors[-10:]:
            print(f"  - {error}")
    
    # Report URL patterns found
    if url_patterns_found:
        print(f"\n→ WorkSpaces-related URLs found ({len(url_patterns_found)}):")
        for url_msg in url_patterns_found[-5:]:
            print(f"  - {url_msg}")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    if not staging_domain_mentions:
        print("CRITICAL: Crawler not accessing staging domain")
        print(f"1. Configure crawler to use {STAGING_DOMAIN} instead of production")
        print("2. Update crawler environment variables to point to staging")
        print("3. Verify staging endpoint configuration in crawler settings")
    
    if future_date_blocks:
        print("\nCRITICAL: Future date blocking detected")
        print("4. Post date (2026-03-02) is in the future - crawler may filter it out")
        print("5. Disable or adjust future date validation for staging environment")
        print("6. Configure crawler to accept dates within reasonable future range")
    
    if not found_target_post:
        print("\n7. Verify the blog post exists and is accessible at staging URL")
        print("8. Check if the publish date filter is excluding posts with date 2026-03-02")
        print(f"9. Verify {STAGING_DOMAIN} has synced this content from production")
        print("10. Check if the crawler's RSS feed includes this category")
        print("11. Verify the crawler's date range configuration allows future dates")
        print("12. Check if there are URL pattern exclusions affecting this post")
    
    if staging_issues:
        print("\n13. Review staging environment connectivity and authentication")
        print("14. Check staging content synchronization from production")
        print("15. Verify staging domain SSL certificates and DNS resolution")
    
    if crawl_errors:
        print("\n16. Review and fix crawler errors for this category")
        print("17. Check rate limiting and timeout configurations")
    
    if not found_category:
        print("\n18. Add 'desktop-and-application-streaming' to crawler configuration")
        print("19. Verify blog category whitelist/blacklist settings")
    
    # Additional staging-specific recommendations
    print("\n" + "=" * 80)
    print("STAGING-SPECIFIC CHECKS")
    print("=" * 80)
    print(f"1. Verify post exists at: {TARGET_URL.replace('aws.amazon.com', STAGING_DOMAIN)}")
    print("2. Check staging crawler configuration points to staging domain")
    print("3. Verify staging environment accepts posts dated 2026-03-02")
    print("4. Review staging content sync status for recent posts")
    print("5. Check staging crawler log group: /aws/lambda/aws-blog-crawler-staging")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
```