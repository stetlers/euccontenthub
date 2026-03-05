```python
import boto3
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import json

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
logs_client = boto3.client('logs', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

# Target blog post details
target_url = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'
expected_date = '2026-03-02'

print("=" * 100)
print("INVESTIGATION: Missing Amazon WorkSpaces Graphics Blog Post (March 2, 2026)")
print("=" * 100)
print()

# Step 1: Check if post exists in DynamoDB
print("STEP 1: Checking DynamoDB for target post...")
print("-" * 100)
try:
    response = table.get_item(Key={'url': target_url})
    
    if 'Item' in response:
        post = response['Item']
        print("✓ POST FOUND in staging database!")
        print(f"  Title: {post.get('title', 'N/A')}")
        print(f"  Source: {post.get('source', 'N/A')}")
        print(f"  Date: {post.get('date', 'N/A')}")
        print(f"  Last crawled: {post.get('last_crawled', 'Never')}")
        print(f"  Authors: {post.get('authors', 'N/A')}")
        print(f"  Has summary: {'Yes' if post.get('summary') else 'No'}")
        print("\n✓ CONCLUSION: Post exists in database. No crawler issue detected.\n")
    else:
        print("✗ POST NOT FOUND in staging database!")
        print(f"  Target URL: {target_url}")
        print(f"  Expected date: {expected_date}")
        print("\n→ Proceeding with further investigation...\n")
except Exception as e:
    print(f"✗ Error checking for specific post: {str(e)}\n")

# Step 2: Verify blog post is accessible via HTTP
print("STEP 2: Verifying blog post accessibility...")
print("-" * 100)
try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(target_url, headers=headers, timeout=30)
    
    print(f"HTTP Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✓ Blog post is accessible")
        
        # Parse the page to extract metadata
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to extract title
        title_tag = soup.find('h1') or soup.find('title')
        if title_tag:
            print(f"  Page Title: {title_tag.get_text().strip()[:100]}")
        
        # Try to extract date
        date_meta = soup.find('meta', {'property': 'article:published_time'}) or \
                    soup.find('meta', {'name': 'publication_date'}) or \
                    soup.find('time')
        if date_meta:
            date_value = date_meta.get('content') or date_meta.get('datetime') or date_meta.get_text()
            print(f"  Published Date: {date_value}")
        
        # Check for author information
        author_meta = soup.find('meta', {'name': 'author'}) or \
                      soup.find('span', class_='author') or \
                      soup.find('a', class_='author')
        if author_meta:
            author_value = author_meta.get('content') or author_meta.get_text()
            print(f"  Author: {author_value.strip()}")
        
        print()
    elif response.status_code == 404:
        print("✗ Blog post returns 404 - Page not found")
        print("  ISSUE: The URL may not exist or has been removed\n")
    elif response.status_code == 403:
        print("✗ Blog post returns 403 - Access forbidden")
        print("  ISSUE: Crawler may be blocked or requires different headers\n")
    else:
        print(f"✗ Unexpected status code: {response.status_code}\n")
        
except requests.exceptions.Timeout:
    print("✗ Request timed out")
    print("  ISSUE: Network connectivity or slow response\n")
except requests.exceptions.RequestException as e:
    print(f"✗ Error accessing blog post: {str(e)}\n")

# Step 3: Check crawler logs
print("STEP 3: Checking crawler logs for errors...")
print("-" * 100)
try:
    # Define possible log group names
    log_group_names = [
        '/aws/lambda/aws-blog-crawler-staging',
        '/aws/lambda/blog-crawler-staging',
        '/ecs/aws-blog-crawler-staging'
    ]
    
    log_found = False
    for log_group_name in log_group_names:
        try:
            # Get recent log events (last 24 hours)
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = end_time - (24 * 60 * 60 * 1000)  # 24 hours ago
            
            # Check if log group exists
            logs_client.describe_log_groups(logGroupNamePrefix=log_group_name, limit=1)
            
            # Get log streams
            streams_response = logs_client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True,
                limit=5
            )
            
            if streams_response['logStreams']:
                log_found = True
                print(f"✓ Found log group: {log_group_name}")
                print(f"  Recent log streams: {len(streams_response['logStreams'])}")
                
                # Search for errors related to the blog or filtering
                filter_patterns = [
                    '?ERROR ?Exception ?Failed',
                    'desktop-and-application-streaming',
                    'workspaces',
                    'filtering',
                    'DynamoDB'
                ]
                
                for pattern in filter_patterns:
                    try:
                        events_response = logs_client.filter_log_events(
                            logGroupName=log_group_name,
                            startTime=start_time,
                            endTime=end_time,
                            filterPattern=pattern,
                            limit=50
                        )
                        
                        if events_response['events']:
                            print(f"\n  → Found {len(events_response['events'])} log entries matching '{pattern}':")
                            for event in events_response['events'][:5]:
                                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                                message = event['message'][:150]
                                print(f"    [{timestamp}] {message}...")
                    except Exception as filter_error:
                        continue
                
                print()
                break
                
        except logs_client.exceptions.ResourceNotFoundException:
            continue
        except Exception as log_error:
            print(f"  Error checking {log_group_name}: {str(log_error)}")
            continue
    
    if not log_found:
        print("✗ No crawler log groups found")
        print("  Checked log groups:", ', '.join(log_group_names))
        print("  ISSUE: Unable to verify crawler execution\n")
        
except Exception as e:
    print(f"✗ Error accessing CloudWatch Logs: {str(e)}\n")

# Step 4: Examine crawler filtering logic by checking similar posts
print("STEP 4: Checking filtering logic - examining similar blog posts...")
print("-" * 100)
try:
    response = table.scan(
        FilterExpression='contains(#url, :blog_path)',
        ExpressionAttributeNames={'#url': 'url'},
        ExpressionAttributeValues={':blog_path': 'aws.amazon.com/blogs/desktop-and-application-streaming/'}
    )
    
    das_posts = response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='contains(#url, :blog_path)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':blog_path': 'aws.amazon.com/blogs/desktop-and-application-streaming/'},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        das_posts.extend(response['Items'])
    
    print(f"✓ Total Desktop and Application Streaming posts in database: {len(das_posts)}")
    
    # Check for posts from March 2026
    march_2026_posts = [p for p in das_posts if p.get('date', '').startswith('2026-03')]
    print(f"  Posts from March 2026: {len(march_2026_posts)}")
    
    # Check for recent posts (last 30 days from expected date)
    recent_posts = [p for p in das_posts if p.get('date', '') >= '2026-02-01']
    print(f"  Posts from Feb 2026 onwards: {len(recent_posts)}")
    
    # Sort and show most recent
    das_posts.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    print("\n  Most recent posts (up to 5):")
    for i, post in enumerate(das_posts[:5], 1):
        print(f"    {i}. [{post.get('date', 'N/A')}] {post.get('title', 'No title')[:60]}...")
        print(f"       Last crawled: {post.get('last_crawled', 'Never')}")
    
    if len(das_posts) > 0:
        latest_date = das_posts[0].get('date', 'Unknown')
        print(f"\n  Latest post date in database: {latest_date}")
        if latest_date < expected_date:
            print(f"  ⚠ WARNING: Latest post is older than expected date ({expected_date})")
            print(f"    ISSUE: Crawler may not have run recently or is not detecting new posts\n")
        else:
            print(f"  ✓ Database contains posts as recent as or newer than target date\n")
    
except Exception as e:
    print(f"✗ Error scanning desktop-and-application-streaming posts: {str(e)}\n")

# Step 5: Verify DynamoDB write permissions and table status
print("STEP 5: Verifying DynamoDB table status and write capability...")
print("-" * 100)
try:
    # Get table description
    table_description = table.meta.client.describe_table(TableName='aws-blog-posts-staging')
    table_status = table_description['Table']['TableStatus']
    item_count = table_description['Table']['ItemCount']
    
    print(f"✓ Table Status: {table_status}")
    print(f"  Total items in table: {item_count}")
    print(f"  Table ARN: {table_description['Table']['TableArn']}")
    
    if table_status == 'ACTIVE':
        print("  ✓ Table is active and available for writes")
    else:
        print(f"  ✗ WARNING: Table status is {table_status}, writes may fail")
    
    # Check for recent writes by examining last_crawled timestamps
    recent_writes = []
    scan_response = table.scan(Limit=100)
    for item in scan_response['Items']:
        last_crawled = item.get('last_crawled', '')
        if last_crawled:
            try:
                crawl_time = datetime.fromisoformat(last_crawled.replace('Z', '+00:00'))
                recent_writes.append(crawl_time)
            except:
                pass
    
    if recent_writes:
        most_recent_write = max(recent_writes)
        hours_since_write = (datetime.now(most_recent_write.tzinfo) - most_recent_write).total_seconds() / 3600
        print(f"  Most recent write: {most_recent_write} ({hours_since_write:.1f} hours ago)")
        
        if hours_since_write > 24:
            print(f"  ⚠ WARNING: No writes in last 24 hours")
            print(f"    ISSUE: Crawler may not be running or DynamoDB writes are failing\n")
        else:
            print(f"  ✓ Recent writes detected - DynamoDB is being updated\n")
    else:
        print("  ✗ WARNING: Unable to determine last write time\n")
    
except Exception as e:
    print(f"✗ Error checking DynamoDB table: {str(e)}\n")

# Step 6: Check Builder.AWS posts for comparison
print("STEP 6: Checking Builder.AWS posts for comparison...")
print("-" * 100)
try:
    response = table.scan(
        FilterExpression='#src = :builder',
        ExpressionAttributeNames={'#src': 'source'},
        ExpressionAttributeValues={':builder': 'builder.aws.com'}
    )

    builder_posts = response['Items']

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='#src = :builder',
            ExpressionAttributeNames={'#src': 'source'},
            ExpressionAttributeValues={':builder': 'builder.aws.com'},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        builder_posts.extend(response['Items'])

    print(f"✓ Total Builder.AWS posts: {len(builder_posts)}")

    # Check for quality issues
    missing_authors = [p for p in builder_posts if p.get('authors') == 'AWS Builder Community']
    missing_summaries = [p for p in builder_posts if not p.get('summary') or p.get('summary') == '']

    print(f"  Posts with generic 'AWS Builder Community' author: {len(missing_authors)}")
    print(f"  Posts without summaries: {len(missing_summaries)}")

    if missing_authors or missing_summaries:
        print("\n  ⚠ Data quality issues detected:")
        print("    Sample posts with generic author (first 3):")
        for i, post in enumerate(missing_authors[:3], 1):
            print(f"      {i}. {post.get('title', 'No title')[:50]}...")
            print(f"         Last crawled: {post.get('last_crawled', 'Never')}")
            print(f"         Has summary: {'Yes' if post.get('summary') else 'No'}")

except Exception as e:
    print(f"✗ Error scanning Builder.AWS posts: {str(e)}\n")

# Final Summary
print()
print("=" * 100)
print("INVESTIGATION SUMMARY")
print("=" * 100)
print()
print("Possible root causes to investigate:")
print("  1. Blog post URL is incorrect or post hasn't been published yet")
print("  2. Crawler schedule may not have run since post publication")
print("  3. Crawler filtering logic may be excluding the post")
print("  4. HTTP access issues (403/404) preventing crawler from fetching content")
print("  5. DynamoDB write failures or permission issues")
print("  6. Crawler exception/error during processing")
print()
print("Next steps:")
print("  • Check crawler execution schedule (CloudWatch Events/EventBridge)")
print("  • Review crawler source code filtering logic")
print("  • Manually trigger crawler if needed")
print("  • Check IAM permissions for DynamoDB writes")