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

print("Investigating staging crawler for Amazon WorkSpaces blog post...")
print("=" * 80)
print(f"Target URL: {TARGET_URL}")
print(f"Target Date: {TARGET_DATE}")
print(f"Blog Category: {BLOG_CATEGORY}")
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
                
                # Check for staging-specific issues
                if 'staging' in message_lower:
                    if any(err in message_lower for err in ['error', 'failed', 'timeout', 'exception']):
                        staging_issues.append(message)
                    elif 'staging.awseuccontent.com' in message_lower:
                        print(f"→ Staging activity: {message}")
                
                # Check for URL pattern issues
                if 'amazon-workspaces' in message_lower or 'workspaces' in message_lower:
                    url_patterns_found.append(message)
                
                # Check for crawler errors
                if any(err in message_lower for err in ['error', 'exception', 'failed', 'timeout']):
                    if BLOG_CATEGORY in message_lower or 'workspaces' in message_lower:
                        crawl_errors.append(message)
                
                # Check for date filtering issues
                if TARGET_DATE in message or 'march 2, 2026' in message_lower or '2026-03-02' in message:
                    print(f"→ Date mention: {message}")
        
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
        print("1. Verify the blog post exists and is accessible at the URL")
        print("2. Check if the publish date filter is excluding recent posts")
        print("3. Verify staging.awseuccontent.com has the latest content")
        print("4. Check if the crawler's RSS feed includes this category")
        print("5. Verify the crawler's date range configuration")
        print("6. Check if there are URL pattern exclusions affecting this post")
    
    if staging_issues:
        print("7. Review staging environment connectivity and authentication")
        print("8. Check staging content synchronization from production")
    
    if crawl_errors:
        print("9. Review and fix crawler errors for this category")
        print("10. Check rate limiting and timeout configurations")
    
    if not found_category:
        print("11. Add 'desktop-and-application-streaming' to crawler configuration")
        print("12. Verify blog category whitelist/blacklist settings")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
```