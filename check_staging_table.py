```python
#!/usr/bin/env python3
"""Check what's in the staging table and debug crawler issues"""

import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

def check_specific_post(search_title):
    """Search for a specific post by title substring"""
    try:
        response = table.scan(
            FilterExpression='contains(title, :title)',
            ExpressionAttributeValues={':title': search_title}
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error searching for specific post: {e}")
        return []

def check_recent_posts(days=7):
    """Check for posts published in the last N days"""
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    try:
        response = table.scan(
            FilterExpression='date_published >= :cutoff',
            ExpressionAttributeValues={':cutoff': cutoff_date}
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error checking recent posts: {e}")
        return []

def check_posts_by_date(target_date):
    """Check for posts published on a specific date"""
    try:
        response = table.scan(
            FilterExpression='date_published = :date',
            ExpressionAttributeValues={':date': target_date}
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error checking posts by date: {e}")
        return []

try:
    # Get total count
    response = table.scan(Select='COUNT')
    total_count = response['Count']
    
    print(f"Total posts in staging: {total_count}")
    
    # Get a few sample posts
    response = table.scan(Limit=5)
    posts = response.get('Items', [])
    
    print(f"\nSample posts:")
    for post in posts:
        print(f"  - {post.get('post_id')}: {post.get('title', 'No title')[:60]}...")
        print(f"    Source: {post.get('source', 'Unknown')}")
        print(f"    Date: {post.get('date_published', 'Unknown')}")
        print()
    
    # Count by source
    response = table.scan()
    all_posts = response.get('Items', [])
    
    aws_blog_count = sum(1 for p in all_posts if 'aws.amazon.com' in p.get('source', ''))
    builder_count = sum(1 for p in all_posts if 'builder.aws.com' in p.get('source', ''))
    
    print(f"Posts by source:")
    print(f"  AWS Blog: {aws_blog_count}")
    print(f"  Builder.AWS: {builder_count}")
    
    # Debug: Check for the specific missing post
    print("\n" + "="*80)
    print("DEBUGGING: Checking for missing post")
    print("="*80)
    
    search_title = "WorkSpaces launches Graphics"
    print(f"\nSearching for posts containing '{search_title}'...")
    matching_posts = check_specific_post(search_title)
    
    if matching_posts:
        print(f"Found {len(matching_posts)} matching post(s):")
        for post in matching_posts:
            print(f"  - {post.get('title')}")
            print(f"    ID: {post.get('post_id')}")
            print(f"    Source: {post.get('source')}")
            print(f"    Date: {post.get('date_published')}")
            print(f"    URL: {post.get('url', 'N/A')}")
    else:
        print("  ❌ No posts found matching the search criteria")
    
    # Check for posts on March 2, 2026
    target_date = '2026-03-02'
    print(f"\nChecking for posts published on {target_date}...")
    posts_on_date = check_posts_by_date(target_date)
    
    if posts_on_date:
        print(f"Found {len(posts_on_date)} post(s) on {target_date}:")
        for post in posts_on_date:
            print(f"  - {post.get('title', 'No title')}")
            print(f"    Source: {post.get('source', 'Unknown')}")
    else:
        print(f"  ❌ No posts found on {target_date}")
    
    # Check recent posts (last 7 days)
    print(f"\nChecking for posts in the last 7 days...")
    recent_posts = check_recent_posts(days=7)
    
    if recent_posts:
        print(f"Found {len(recent_posts)} recent post(s):")
        for post in sorted(recent_posts, key=lambda x: x.get('date_published', ''), reverse=True)[:10]:
            print(f"  - [{post.get('date_published')}] {post.get('title', 'No title')[:60]}...")
    else:
        print("  ❌ No recent posts found in the last 7 days")
    
    # Check for future dates (crawler date filtering issue)
    print(f"\nChecking for posts with future dates...")
    future_posts = [p for p in all_posts if p.get('date_published', '') > datetime.now().strftime('%Y-%m-%d')]
    
    if future_posts:
        print(f"⚠️  WARNING: Found {len(future_posts)} post(s) with future dates:")
        for post in sorted(future_posts, key=lambda x: x.get('date_published', ''), reverse=True)[:10]:
            print(f"  - [{post.get('date_published')}] {post.get('title', 'No title')[:60]}...")
    else:
        print("  ✓ No posts with future dates found")
    
    # Summary of latest posts
    print(f"\n" + "="*80)
    print("Latest 10 posts by publication date:")
    print("="*80)
    sorted_posts = sorted(all_posts, key=lambda x: x.get('date_published', ''), reverse=True)[:10]
    for post in sorted_posts:
        print(f"  [{post.get('date_published')}] {post.get('title', 'No title')[:60]}...")
        print(f"    Source: {post.get('source', 'Unknown')}")
    
    print("\n" + "="*80)
    print("NEXT STEPS FOR DEBUGGING:")
    print("="*80)
    print("1. Check if the post exists on the source website (aws.amazon.com/blogs/)")
    print("2. Verify the crawler is running and check CloudWatch logs")
    print("3. Check if date filtering in crawler is blocking future dates")
    print("4. Verify URL patterns in crawler configuration")
    print("5. Check for any errors in the crawler's RSS/feed parser")
    print("6. Ensure the crawler's last run timestamp is recent")
    
except ClientError as e:
    print(f"Error accessing DynamoDB table: {e}")
    print("Verify:")
    print("  - Table 'aws-blog-posts-staging' exists in us-east-1")
    print("  - AWS credentials are configured correctly")
    print("  - IAM permissions include dynamodb:Scan and dynamodb:Query")
except Exception as e:
    print(f"Unexpected error: {e}")
```