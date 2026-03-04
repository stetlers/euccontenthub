```python
import boto3
from decimal import Decimal
from datetime import datetime

# Connect to staging DynamoDB table
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

# Define the specific blog post we're looking for
TARGET_URL = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'
TARGET_DATE = '2026-03-02'

print(f"\n{'='*80}")
print(f"Investigating Missing Amazon WorkSpaces Blog Post")
print(f"{'='*80}")
print(f"Target URL: {TARGET_URL}")
print(f"Expected Date: {TARGET_DATE}")
print(f"{'='*80}\n")

# Check if the specific blog post exists
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
    print(f"Error during specific post search: {str(e)}")

print(f"\n{'='*80}")

# Original Builder.AWS posts status check
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

    print(f"\n{'='*80}")
    print(f"Builder.AWS Posts Status in Staging")
    print(f"{'='*80}")
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
    print(f"Error during Builder.AWS posts check: {str(e)}")

# Summary and recommendations
print(f"\n{'='*80}")
print(f"RECOMMENDATIONS")
print(f"{'='*80}")
print(f"1. Verify the crawler configuration includes 'desktop-and-application-streaming' blog")
print(f"2. Check crawler logs for errors when processing this URL")
print(f"3. Verify the blog post is publicly accessible at the target URL")
print(f"4. Check if there are URL encoding or redirect issues")
print(f"5. Ensure the crawler is running and completing successfully")
print(f"6. Verify the publish date is being parsed correctly from the blog post")
print(f"{'='*80}\n")
```