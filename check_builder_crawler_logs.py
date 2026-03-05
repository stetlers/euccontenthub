```python
"""
Check for Amazon WorkSpaces blog post and staging crawler issues
Enhanced with detailed date filtering, URL pattern analysis, and storage verification
"""
import boto3
import json
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')
dynamodb = boto3.client('dynamodb', region_name='us-east-1')
s3_client = boto3.client('s3', region_name='us-east-1')

log_group = '/aws/lambda/aws-blog-crawler'

# Target blog post details
TARGET_URL = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'
TARGET_DATE = '2026-03-02'
TARGET_DATE_VARIANTS = ['2026-03-02', '2026/03/02', 'march 2, 2026', 'march 2nd, 2026', '3/2/2026', '03/02/2026']
BLOG_CATEGORY = 'desktop-and-application-streaming'
TARGET_KEYWORDS = ['graphics g6', 'gr6', 'g6f', 'workspaces-launches-graphics']

# Storage locations to check
DYNAMODB_TABLE = 'aws-blog-posts'
S3_BUCKET = 'aws-blog-crawler-staging'

print("Investigating staging crawler for Amazon WorkSpaces blog post...")
print("=" * 80)
print(f"Target URL: {TARGET_URL}")
print(f"Target Date: {TARGET_DATE}")
print(f"Blog Category: {BLOG_CATEGORY}")
print(f"Keywords: {', '.join(TARGET_KEYWORDS)}")
print("=" * 80)

# Check if post exists in storage
def check_dynamodb_storage():
    """Check if the blog post exists in DynamoDB"""
    print("\n→ Checking DynamoDB storage...")
    try:
        response = dynamodb.scan(
            TableName=DYNAMODB_TABLE,
            FilterExpression='contains(#url, :url_part) OR contains(title, :keyword)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={
                ':url_part': {'S': 'workspaces-launches-graphics-g6'},
                ':keyword': {'S': 'Graphics G6'}
            },
            Limit=100
        )
        
        items = response.get('Items', [])
        if items:
            print(f"✓ Found {len(items)} matching items in DynamoDB")
            for item in items:
                url = item.get('url', {}).get('S', 'N/A')
                title = item.get('title', {}).get('S', 'N/A')
                date = item.get('publish_date', {}).get('S', 'N/A')
                print(f"  - {title} ({date})")
                print(f"    URL: {url}")
            return True
        else:
            print("✗ Post NOT FOUND in DynamoDB")
            return False
    except Exception as e:
        print(f"⚠ Error checking DynamoDB: {e}")
        return False

def check_s3_storage():
    """Check if the blog post exists in S3"""
    print("\n→ Checking S3 storage...")
    try:
        # Check for files with the target date
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f'blog-posts/{TARGET_DATE.replace("-", "/")}/'
        )
        
        if 'Contents' in response:
            print(f"✓ Found {len(response['Contents'])} objects for target date in S3")
            for obj in response['Contents']:
                print(f"  - {obj['Key']} (Size: {obj['Size']} bytes)")
            return True
        else:
            print("✗ No objects found for target date in S3")
            
        # Also check for any WorkSpaces-related posts
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix='blog-posts/',
            MaxKeys=1000
        )
        
        workspaces_posts = []
        if 'Contents' in response:
            for obj in response['Contents']:
                if 'workspaces' in obj['Key'].lower():
                    workspaces_posts.append(obj['Key'])
        
        if workspaces_posts:
            print(f"→ Found {len(workspaces_posts)} WorkSpaces-related posts in S3:")
            for post_key in workspaces_posts[-5:]:
                print(f"  - {post_key}")
        
        return False
    except Exception as e:
        print(f"⚠ Error checking S3: {e}")
        return False

# Check storage first
stored_in_dynamodb = check_dynamodb_storage()
stored_in_s3 = check_s3_storage()

try:
    # Get log streams from the last 7 days
    start_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
    
    streams = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=20  # Increased to analyze more streams
    )
    
    if not streams['logStreams']:
        print("\nERROR: No log streams found. Crawler may not be running.")
        exit(1)
    
    print(f"\nAnalyzing {len(streams['logStreams'])} recent log streams...\n")
    
    found_target_post = False
    found_category = False
    crawl_errors = []
    staging_issues = []
    url_patterns_found = []
    date_filters_found = []
    rss_feed_entries = []
    storage_attempts = []
    
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
                if TARGET_URL in message or any(keyword in message_lower for keyword in TARGET_KEYWORDS):
                    found_target_post = True
                    print(f"✓ FOUND TARGET POST: {message}")
                
                # Check for blog category crawling
                if BLOG_CATEGORY in message_lower or 'desktop-and-application-streaming' in message_lower:
                    found_category = True
                    if 'crawling' in message_lower or 'processing' in message_lower:
                        print(f"✓ Category being crawled: {message}")
                
                # Check for date filtering logic
                if any(date_var in message for date_var in TARGET_DATE_VARIANTS) or 'date filter' in message_lower or 'date range' in message_lower:
                    date_filters_found.append(message)
                    print(f"→ Date filtering: {message}")
                
                # Check for RSS feed parsing
                if 'rss' in message_lower and ('feed' in message_lower or 'entry' in message_lower or 'item' in message_lower):
                    rss_feed_entries.append(message)
                    if BLOG_CATEGORY in message_lower or 'workspaces' in message_lower:
                        print(f"→ RSS feed entry: {message}")
                
                # Check for storage operations
                if any(storage in message_lower for storage in ['dynamodb', 's3', 'storing', 'saving', 'persisting']):
                    if any(keyword in message_lower for keyword in TARGET_KEYWORDS + ['workspaces']):
                        storage_attempts.append(message)
                        print(f"→ Storage operation: {message}")
                
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
                    if BLOG_CATEGORY in message_lower or any(keyword in message_lower for keyword in TARGET_KEYWORDS + ['workspaces']):
                        crawl_errors.append(message)
        
        except Exception as stream_error:
            print(f"Warning: Could not process stream {stream_name}: {stream_error}")
            continue
    
    # Report findings
    print("\n" + "=" * 80)
    print("DIAGNOSTIC REPORT")
    print("=" * 80)
    
    print("\n### STORAGE STATUS ###")
    if stored_in_dynamodb:
        print("✓ Post EXISTS in DynamoDB")
    else:
        print("✗ Post NOT FOUND in DynamoDB")
    
    if stored_in_s3:
        print("✓ Post EXISTS in S3")
    else:
        print("✗ Post NOT FOUND in S3")
    
    print("\n### CRAWLER DETECTION ###")
    if found_target_post:
        print("✓ Target blog post WAS DETECTED by crawler logs")
    else:
        print("✗ Target blog post NOT DETECTED by crawler logs")
        print("  → The crawler did not detect or process this post")
    
    if found_category:
        print(f"✓ Blog category '{BLOG_CATEGORY}' is being crawled")
    else:
        print(f"✗ Blog category '{BLOG_CATEGORY}' may not be in crawler scope")
    
    # Report date filtering
    if date_filters_found:
        print(f"\n### DATE FILTERING ({len(date_filters_found)} instances) ###")
        for date_filter in date_filters_found[-10:]:
            print(f"  - {date_filter}")
    else:
        print("\n⚠ NO DATE FILTERING logic found in logs")
        print("  → This may indicate date filter is not logging or not active")
    
    # Report RSS feed parsing
    if rss_feed_entries:
        print(f"\n### RSS FEED PARSING ({len(rss_feed_entries)} entries) ###")
        for rss_entry in rss_feed_entries[-10:]:
            print(f"  - {rss_entry}")
    else:
        print("\n⚠ NO RSS FEED entries found in logs")
        print("  → RSS feed may not be fetched or parsed correctly")
    
    # Report storage attempts
    if storage_attempts:
        print(f"\n### STORAGE ATTEMPTS ({len(storage_attempts)}) ###")
        for storage_msg in storage_attempts[-10:]:
            print(f"  - {storage_msg}")
    else:
        print("\n⚠ NO STORAGE ATTEMPTS found for WorkSpaces posts")
        print("  → Posts may be filtered before storage or storage is failing silently")
    
    # Report staging issues
    if staging_issues:
        print(f"\n### STAGING ISSUES ({len(staging_issues)}) ###")
        for issue in staging_issues[-10:]:
            print(f"  - {issue}")
    
    # Report crawler errors
    if crawl_errors:
        print(f"\n### CRAWLER ERRORS ({len(crawl_errors)}) ###")
        for error in crawl_errors[-10:]:
            print(f"  - {error}")
    
    # Report URL patterns found
    if url_patterns_found:
        print(f"\n### WORKSPACES-RELATED URLS ({len(url_patterns_found)}) ###")
        for url_msg in url_patterns_found[-10:]:
            print(f"  - {url_msg}")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    if not stored_in_dynamodb and not stored_in_s3 and not found_target_post:
        print("\n⚠ CRITICAL: Post not detected by crawler and not stored")
        print("1. Verify the blog post exists and is published at the URL")
        print("2. Check if the RSS feed for this category includes the post")
        print("3. Verify staging.awseuccontent.com has synchronized this content")
        print("4. Check crawler's category whitelist configuration")
    
    if found_target_post and not stored_in_dynamodb and not stored_in_s3:
        print("\n⚠ CRITICAL: Post detected but not stored")
        print("5. Check storage permissions (DynamoDB/S3 write permissions)")
        print("6. Review storage error handling and retry logic")
        print("7. Check if post is being filtered after detection")
    
    if not date_filters_found:
        print("\n8. Enable date filter logging to debug date range issues")
        print("9. Verify crawler's date range configuration (check for hardcoded cutoff dates)")
        print("10. Ensure future dates (2026) are not being filtered out")
    
    if not rss_feed_entries:
        print("\n11. Check RSS feed URL configuration for this category")
        print("12. Verify RSS feed is accessible from crawler environment")
        print("13. Check if RSS feed parser is working correctly")
    
    if staging_issues:
        print("\n14. Review staging environment connectivity and authentication")
        print("15. Check staging content synchronization from production")
        print("16. Verify staging.awseuccontent.com SSL certificates")
    
    if crawl_errors:
        print("\n17. Review and fix crawler errors for this category")
        print("18. Check rate limiting and timeout configurations")
        print("19. Implement retry logic for transient failures")
    
    if not found_category:
        print("\n20. Add 'desktop-and-application-streaming' to crawler configuration")
        print("21. Verify blog category whitelist/blacklist settings")
        print("22. Check if category URL patterns are correctly configured")
    
    print("\n### NEXT STEPS ###")
    print("1. Run crawler in debug mode with verbose logging")
    print("2. Manually test RSS feed: https://aws.amazon.com/blogs/desktop-and-application-streaming/feed/")
    print("3. Check crawler schedule - ensure it runs frequently enough")
    print("4. Verify the post's publish date in the RSS feed")
    print("5. Test URL pattern matching against target URL")
    print("6. Review crawler source code for date filtering logic")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
```