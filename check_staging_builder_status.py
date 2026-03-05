```python
import boto3
import requests
from decimal import Decimal
from datetime import datetime
import json
from botocore.exceptions import ClientError

# Connect to staging DynamoDB table
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

# Connect to CloudWatch Logs for crawler log analysis
logs_client = boto3.client('logs', region_name='us-east-1')

# Define the specific blog post we're looking for
TARGET_URL = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'
TARGET_DATE = '2026-03-02'
CRAWLER_LOG_GROUP = '/aws/lambda/staging-blog-crawler'
BUILDER_LOG_GROUP = '/aws/lambda/staging-blog-builder'

print(f"\n{'='*80}")
print(f"Investigating Missing Amazon WorkSpaces Blog Post")
print(f"{'='*80}")
print(f"Target URL: {TARGET_URL}")
print(f"Expected Date: {TARGET_DATE}")
print(f"{'='*80}\n")

# Step 1: Verify blog post accessibility
print(f"STEP 1: Verifying Blog Post Accessibility")
print(f"{'-'*80}")
try:
    response = requests.get(TARGET_URL, timeout=10, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; AWS-Blog-Crawler/1.0)'
    })
    print(f"✓ HTTP Status: {response.status_code}")
    print(f"✓ Content Length: {len(response.content)} bytes")
    print(f"✓ Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
    
    if response.status_code == 200:
        print(f"✓ Blog post is publicly accessible")
        # Check for key content indicators
        content = response.text.lower()
        if 'workspaces' in content and 'graphics' in content:
            print(f"✓ Content contains expected keywords")
        else:
            print(f"⚠ Warning: Content may not contain expected keywords")
    else:
        print(f"✗ Blog post returned non-200 status code")
        
except requests.exceptions.RequestException as e:
    print(f"✗ Error accessing blog post: {str(e)}")
    print(f"  This may indicate network issues or the post is not publicly available")

print(f"\n")

# Step 2: Check DynamoDB for the specific post
print(f"STEP 2: Checking DynamoDB for Target Post")
print(f"{'-'*80}")
try:
    response = table.scan(
        FilterExpression='contains(#url, :url_part)',
        ExpressionAttributeNames={'#url': 'url'},
        ExpressionAttributeValues={':url_part': 'amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles'}
    )
    
    if response['Items']:
        print(f"✓ FOUND the target blog post in staging!")
        for post in response['Items']:
            print(f"\n  Post ID: {post['post_id']}")
            print(f"  Title: {post.get('title', 'No title')}")
            print(f"  URL: {post.get('url', 'No URL')}")
            print(f"  Date: {post.get('publish_date', 'No date')}")
            print(f"  Source: {post.get('source', 'No source')}")
            print(f"  Has Summary: {bool(post.get('summary'))}")
            print(f"  Has Content: {bool(post.get('content'))}")
            print(f"  Created At: {post.get('created_at', 'Unknown')}")
    else:
        print(f"✗ Target blog post NOT FOUND in staging table")
        
        # Check for any desktop-and-application-streaming blog posts
        print(f"\nChecking for any posts from desktop-and-application-streaming blog...")
        response_das = table.scan(
            FilterExpression='contains(#url, :blog_category)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':blog_category': 'desktop-and-application-streaming'}
        )
        
        das_posts = response_das['Items']
        if das_posts:
            print(f"Found {len(das_posts)} posts from this blog category:")
            for post in sorted(das_posts, key=lambda x: x.get('publish_date', ''), reverse=True)[:10]:
                print(f"  - {post.get('publish_date', 'No date')}: {post.get('title', 'No title')[:80]}")
        else:
            print(f"✗ NO posts found from desktop-and-application-streaming blog")
            print(f"  This indicates the crawler may not be crawling this blog category")
        
        # Check for recent posts around the target date
        print(f"\nChecking for any posts published around {TARGET_DATE}...")
        response_recent = table.scan(
            FilterExpression='#date >= :start_date AND #date <= :end_date',
            ExpressionAttributeNames={'#date': 'publish_date'},
            ExpressionAttributeValues={
                ':start_date': '2026-03-01',
                ':end_date': '2026-03-03'
            }
        )
        
        recent_posts = response_recent['Items']
        if recent_posts:
            print(f"Found {len(recent_posts)} posts from March 1-3, 2026:")
            for post in sorted(recent_posts, key=lambda x: x.get('publish_date', '')):
                print(f"  - {post.get('publish_date', 'No date')}: {post.get('title', 'No title')[:80]}")
                print(f"    Source: {post.get('source', 'No source')}")
        else:
            print(f"✗ NO posts found from March 1-3, 2026")
            print(f"  This may indicate the crawler is not processing recent content")

except Exception as e:
    print(f"✗ Error during DynamoDB search: {str(e)}")

print(f"\n")

# Step 3: Examine crawler logs
print(f"STEP 3: Examining Crawler Logs")
print(f"{'-'*80}")
try:
    # Get recent log streams (last 24 hours)
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = end_time - (24 * 60 * 60 * 1000)
    
    try:
        log_streams_response = logs_client.describe_log_streams(
            logGroupName=CRAWLER_LOG_GROUP,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        if log_streams_response['logStreams']:
            print(f"✓ Found {len(log_streams_response['logStreams'])} recent crawler log streams")
            
            # Search for relevant log entries
            error_patterns = [
                'desktop-and-application-streaming',
                'workspaces',
                'graphics-g6',
                'error',
                'exception',
                'failed',
                'timeout'
            ]
            
            for pattern in error_patterns:
                try:
                    filter_response = logs_client.filter_log_events(
                        logGroupName=CRAWLER_LOG_GROUP,
                        startTime=start_time,
                        endTime=end_time,
                        filterPattern=f'"{pattern}"',
                        limit=10
                    )
                    
                    if filter_response['events']:
                        print(f"\n  Found {len(filter_response['events'])} log entries matching '{pattern}':")
                        for event in filter_response['events'][:3]:
                            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                            message = event['message'][:200]
                            print(f"    [{timestamp}] {message}")
                except ClientError as e:
                    if e.response['Error']['Code'] != 'ResourceNotFoundException':
                        print(f"  ⚠ Error searching for pattern '{pattern}': {str(e)}")
        else:
            print(f"✗ No recent crawler log streams found")
            print(f"  The crawler may not be running")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"✗ Crawler log group '{CRAWLER_LOG_GROUP}' not found")
            print(f"  Please verify the correct log group name")
        else:
            raise

except Exception as e:
    print(f"✗ Error examining crawler logs: {str(e)}")

print(f"\n")

# Step 4: Test DynamoDB write capability
print(f"STEP 4: Testing DynamoDB Write Capability")
print(f"{'-'*80}")
try:
    test_item = {
        'post_id': f'test-write-{int(datetime.now().timestamp())}',
        'url': 'https://test-write-capability.example.com',
        'title': 'Test Write Capability',
        'publish_date': datetime.now().strftime('%Y-%m-%d'),
        'source': 'test',
        'created_at': datetime.now().isoformat()
    }
    
    # Attempt to write test item
    table.put_item(Item=test_item)
    print(f"✓ Successfully wrote test item to DynamoDB")
    
    # Verify the write
    response = table.get_item(Key={'post_id': test_item['post_id']})
    if 'Item' in response:
        print(f"✓ Successfully retrieved test item from DynamoDB")
        # Clean up test item
        table.delete_item(Key={'post_id': test_item['post_id']})
        print(f"✓ Successfully deleted test item (cleanup)")
    else:
        print(f"✗ Could not retrieve test item after write")
        
except Exception as e:
    print(f"✗ Error testing DynamoDB write: {str(e)}")
    print(f"  This may indicate IAM permission issues or DynamoDB problems")

print(f"\n")

# Step 5: Check crawler filtering logic indicators
print(f"STEP 5: Analyzing Crawler Filtering Logic")
print(f"{'-'*80}")
try:
    # Sample recent posts to understand filtering patterns
    response = table.scan(Limit=100)
    posts = response['Items']
    
    # Analyze URL patterns
    url_domains = {}
    blog_categories = {}
    
    for post in posts:
        url = post.get('url', '')
        if 'aws.amazon.com/blogs/' in url:
            category = url.split('/blogs/')[-1].split('/')[0]
            blog_categories[category] = blog_categories.get(category, 0) + 1
        
        # Extract domain
        if url.startswith('http'):
            domain = url.split('/')[2]
            url_domains[domain] = url_domains.get(domain, 0) + 1
    
    print(f"Analyzed {len(posts)} posts from staging table")
    print(f"\nBlog Categories Found:")
    for category, count in sorted(blog_categories.items(), key=lambda x: x[1], reverse=True)[:15]:
        marker = "✓" if category == "desktop-and-application-streaming" else " "
        print(f"  {marker} {category}: {count} posts")
    
    if 'desktop-and-application-streaming' not in blog_categories:
        print(f"\n✗ 'desktop-and-application-streaming' category NOT found in crawled data")
        print(f"  This indicates the crawler is likely filtering out this category")
    
    print(f"\nDomains Found:")
    for domain, count in sorted(url_domains.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {domain}: {count} posts")

except Exception as e:
    print(f"✗ Error analyzing filtering logic: {str(e)}")

print(f"\n")

# Original Builder.AWS posts status check
print(f"{'='*80}")
print(f"Builder.AWS Posts Status in Staging")
print(f"{'='*80}")
try:
    response = table.scan(
        FilterExpression='#src = :builder',
        ExpressionAttributeNames={'#src': 'source'},
        ExpressionAttributeValues={':builder': 'builder.aws.com'}
    )

    posts = response['Items']

    # Count posts by status
    total = len(posts)
    with_authors = sum(1 for p in posts if p.get('authors') and p['authors'] != 'AWS Builder Community')
    with_summaries = sum(1 for p in posts if p.get('summary'))
    with_labels = sum(1 for p in posts if p.get('label'))
    with_content = sum(1 for p in posts if p.get('content') and len(p['content']) > 100)

    print(f"Total posts: {total}")
    print(f"Posts with real authors: {with_authors}/{total}")
    print(f"Posts with content (>100 chars): {with_content}/{total}")
    print(f"Posts with summaries: {with_summaries}/{total}")
    print(f"Posts with labels: {with_labels}/{total}")
    print(f"{'='*80}\n")

    # Show sample of posts without summaries
    posts_without_summaries = [p for p in posts if not p.get('summary')]
    if posts_without_summaries:
        print(f"\nSample posts WITHOUT summaries (showing first 5):")
        for i, post in enumerate(posts_without_summaries[:5], 1):
            print(f"\n{i}. {post.get('title', 'No title')}")
            print(f"   Post ID: {post['post_id']}")
            print(f"   Author: {post.get('authors', 'No author')}")
            print(f"   Has content: {bool(post.get('content') and len(post['content']) > 100)}")
            print(f"   Content length: {len(post.get('content', ''))}")

except Exception as e:
    print(f"✗ Error during Builder.AWS posts check: {str(e)}")

# Summary and recommendations
print(f"\n{'='*80}")
print(f"DIAGNOSTIC SUMMARY & RECOMMENDATIONS")
print(f"{'='*80}")
print(f"\nImmediate Actions:")
print(f"1. ✓ Verify the blog post is publicly accessible (completed above)")
print(f"2. ✓ Check if post exists in DynamoDB staging table (completed above)")
print(f"3. ✓ Examine crawler logs for errors (completed above)")
print(f"4. ✓ Test DynamoDB write capability (completed above)")
print(f"5. ✓ Analyze crawler filtering patterns (completed above)")

print(f"\nIf Post Not Found:")
print(f"- Check if 'desktop-and-application-streaming' is in crawler configuration")
print(f"- Review crawler's RSS feed sources list")
print(f"- Verify crawler is running on schedule (check EventBridge/CloudWatch)")
print(f"- Check for URL encoding or redirect issues")
print(f"- Verify publish date parsing logic handles this blog's date format")
print(f"- Review IAM permissions for crawler Lambda function")

print(f"\nIf Post Found But Incomplete:")
print(f"- Review builder Lambda logs for processing errors")
print(f"- Check content extraction logic for this blog category")
print(f"- Verify AI summarization service is functioning")

print(f"\nLog Locations to Check:")
print(f"- Crawler logs: {CRAWLER_LOG_GROUP}")
print(f"-