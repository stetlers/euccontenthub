```python
"""
Investigate why Amazon WorkSpaces Graphics blog post (March 2, 2026) is not being detected
by the staging crawler. This script checks:
1. If the post exists in DynamoDB
2. Crawler logs for any errors
3. Recent posts added to verify crawler is working
4. DynamoDB write operations
"""
import boto3
from datetime import datetime, timedelta
from collections import Counter

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
logs_client = boto3.client('logs', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("=" * 80)
print("INVESTIGATING MISSING BLOG POST - March 2, 2026")
print("Amazon WorkSpaces Graphics bundles")
print("=" * 80)

# 1. Check if the specific post exists in DynamoDB
print("\n1. Checking if WorkSpaces Graphics post exists in DynamoDB...")
print("-" * 80)

try:
    response = table.scan()
    all_posts = response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        all_posts.extend(response['Items'])
    
    print(f"Total posts in staging table: {len(all_posts)}")
    
    # Search for WorkSpaces related posts
    workspaces_posts = [p for p in all_posts if 'workspaces' in p.get('title', '').lower() or 
                        'workspaces' in p.get('url', '').lower()]
    
    print(f"\nWorkSpaces-related posts found: {len(workspaces_posts)}")
    
    # Check for March 2026 posts
    march_2026_posts = []
    for post in all_posts:
        pub_date = post.get('published_date', '')
        if '2026-03' in pub_date or 'March 2, 2026' in pub_date or '2026-03-02' in pub_date:
            march_2026_posts.append(post)
    
    print(f"Posts from March 2026: {len(march_2026_posts)}")
    
    # Search specifically for Graphics bundle post
    graphics_post = None
    for post in all_posts:
        title = post.get('title', '').lower()
        content = post.get('content', '').lower()
        if ('graphics' in title or 'graphics' in content) and 'workspaces' in (title + content):
            if '2026-03' in post.get('published_date', ''):
                graphics_post = post
                break
    
    if graphics_post:
        print("\n✅ TARGET POST FOUND:")
        print(f"  • Title: {graphics_post.get('title')}")
        print(f"  • URL: {graphics_post.get('url')}")
        print(f"  • Published: {graphics_post.get('published_date')}")
        print(f"  • Post ID: {graphics_post.get('post_id')}")
    else:
        print("\n❌ TARGET POST NOT FOUND in DynamoDB")
        
        # Show recent WorkSpaces posts for comparison
        if workspaces_posts:
            print("\nRecent WorkSpaces posts for reference:")
            for post in sorted(workspaces_posts, 
                             key=lambda x: x.get('published_date', ''), 
                             reverse=True)[:5]:
                print(f"  • {post.get('published_date')} - {post.get('title')[:60]}")

except Exception as e:
    print(f"❌ Error scanning DynamoDB: {str(e)}")

# 2. Check recent posts to verify crawler is working
print("\n2. Checking recent posts to verify crawler activity...")
print("-" * 80)

try:
    # Get posts from last 7 days
    recent_cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    recent_posts = [p for p in all_posts if p.get('published_date', '') >= recent_cutoff]
    
    print(f"Posts added in last 7 days: {len(recent_posts)}")
    
    if recent_posts:
        print("\nMost recent posts:")
        for post in sorted(recent_posts, 
                         key=lambda x: x.get('published_date', ''), 
                         reverse=True)[:10]:
            print(f"  • {post.get('published_date')} - {post.get('title')[:60]}")
            print(f"    Source: {post.get('source', 'N/A')}")
    else:
        print("⚠️  WARNING: No posts added in the last 7 days!")
        print("   This suggests the crawler may not be running.")

except Exception as e:
    print(f"❌ Error checking recent posts: {str(e)}")

# 3. Check CloudWatch Logs for crawler errors
print("\n3. Checking CloudWatch Logs for crawler errors...")
print("-" * 80)

try:
    log_group_name = '/aws/lambda/blog-crawler-staging'
    
    # Get logs from last 24 hours
    start_time = int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)
    end_time = int(datetime.now().timestamp() * 1000)
    
    # Check if log group exists
    try:
        log_streams_response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        print(f"Found {len(log_streams_response.get('logStreams', []))} recent log streams")
        
        # Search for errors and warnings
        filter_patterns = [
            'ERROR',
            'Exception',
            'WorkSpaces',
            'Graphics',
            'DynamoDB',
            'failed'
        ]
        
        for pattern in filter_patterns:
            try:
                events_response = logs_client.filter_log_events(
                    logGroupName=log_group_name,
                    startTime=start_time,
                    endTime=end_time,
                    filterPattern=pattern,
                    limit=10
                )
                
                events = events_response.get('events', [])
                if events:
                    print(f"\nLog entries matching '{pattern}': {len(events)}")
                    for event in events[:3]:
                        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                        print(f"  • [{timestamp}] {event['message'][:100]}")
                        
            except Exception as e:
                print(f"  Could not filter logs for pattern '{pattern}': {str(e)}")
                
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"⚠️  Log group '{log_group_name}' not found")
        print("   The crawler may not have run yet or logs are not configured")
    
except Exception as e:
    print(f"❌ Error accessing CloudWatch Logs: {str(e)}")

# 4. Verify DynamoDB write operations
print("\n4. Verifying DynamoDB write operations...")
print("-" * 80)

try:
    # Check table status
    table_description = dynamodb.meta.client.describe_table(
        TableName='aws-blog-posts-staging'
    )
    
    table_status = table_description['Table']['TableStatus']
    item_count = table_description['Table']['ItemCount']
    
    print(f"Table Status: {table_status}")
    print(f"Item Count: {item_count}")
    
    if table_status != 'ACTIVE':
        print("⚠️  WARNING: Table is not in ACTIVE state!")
    else:
        print("✅ Table is ACTIVE and accepting writes")
    
    # Check for write throttling or errors in CloudWatch Metrics
    cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
    
    metrics_response = cloudwatch.get_metric_statistics(
        Namespace='AWS/DynamoDB',
        MetricName='UserErrors',
        Dimensions=[
            {'Name': 'TableName', 'Value': 'aws-blog-posts-staging'}
        ],
        StartTime=datetime.now() - timedelta(hours=24),
        EndTime=datetime.now(),
        Period=3600,
        Statistics=['Sum']
    )
    
    if metrics_response['Datapoints']:
        total_errors = sum(dp['Sum'] for dp in metrics_response['Datapoints'])
        print(f"\nDynamoDB UserErrors (last 24h): {int(total_errors)}")
        if total_errors > 0:
            print("⚠️  WARNING: DynamoDB write errors detected!")
    else:
        print("\n✅ No DynamoDB errors in last 24 hours")

except Exception as e:
    print(f"❌ Error checking DynamoDB status: {str(e)}")

# 5. Check for deduplication issues
print("\n5. Checking for deduplication issues...")
print("-" * 80)

try:
    # Check for duplicate post IDs
    post_ids = [p.get('post_id') for p in all_posts]
    unique_post_ids = set(post_ids)
    
    print(f"Total posts: {len(post_ids)}")
    print(f"Unique post IDs: {len(unique_post_ids)}")
    print(f"Duplicate post IDs: {len(post_ids) - len(unique_post_ids)}")
    
    if len(post_ids) != len(unique_post_ids):
        print("\n⚠️  DUPLICATE POST IDs FOUND:")
        id_counts = Counter(post_ids)
        for post_id, count in id_counts.items():
            if count > 1:
                print(f"  • {post_id} (appears {count} times)")
    else:
        print("✅ No duplicate post IDs found")
    
    # Check for duplicate URLs
    urls = [p.get('url') for p in all_posts]
    unique_urls = set(urls)
    
    print(f"\nUnique URLs: {len(unique_urls)}")
    print(f"Duplicate URLs: {len(urls) - len(unique_urls)}")
    
    if len(urls) != len(unique_urls):
        print("\n⚠️  DUPLICATE URLs FOUND:")
        url_counts = Counter(urls)
        for url, count in url_counts.items():
            if count > 1:
                print(f"  • {url} (appears {count} times)")
    else:
        print("✅ No duplicate URLs found")

except Exception as e:
    print(f"❌ Error checking for duplicates: {str(e)}")

# 6. Summary and recommendations
print("\n" + "=" * 80)
print("SUMMARY AND RECOMMENDATIONS")
print("=" * 80)

print("\nNext Steps:")
print("1. If post not found: Check if blog post is published and accessible")
print("2. If no recent activity: Verify crawler Lambda is scheduled and running")
print("3. If errors in logs: Review error messages and fix issues")
print("4. If DynamoDB errors: Check IAM permissions and capacity settings")
print("5. If duplicates found: Review deduplication logic in crawler code")
print("\nTo manually trigger crawler, run:")
print("  aws lambda invoke --function-name blog-crawler-staging response.json")
```