```python
"""
Check detailed status of Builder.AWS posts in staging and investigate specific post detection issues
"""
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("Checking Builder.AWS posts status in staging...")
print("=" * 80)

# First, check for the specific post that should be detected
specific_post_title = "Amazon WorkSpaces launches Graphics G6, Gr6, and G6f bundles"
specific_post_date = "2026-03-02"

print(f"\n🔍 INVESTIGATING SPECIFIC POST:")
print("-" * 80)
print(f"Title: {specific_post_title}")
print(f"Expected Date: {specific_post_date}")
print(f"Expected Source: staging.awseuccontent.com\n")

# Search for the specific post by title
try:
    response = table.scan(
        FilterExpression='contains(title, :title_part)',
        ExpressionAttributeValues={':title_part': 'Amazon WorkSpaces launches Graphics'}
    )
    
    specific_posts = response['Items']
    
    # Handle pagination for specific post search
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='contains(title, :title_part)',
            ExpressionAttributeValues={':title_part': 'Amazon WorkSpaces launches Graphics'},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        specific_posts.extend(response['Items'])
    
    if specific_posts:
        print(f"✓ Found {len(specific_posts)} matching post(s):")
        for post in specific_posts:
            print(f"  • Title: {post.get('title')}")
            print(f"    Source: {post.get('source', 'N/A')}")
            print(f"    Date: {post.get('published_date', 'N/A')}")
            print(f"    URL: {post.get('url', 'N/A')}")
            print(f"    Authors: {post.get('authors', 'N/A')}")
            print()
    else:
        print(f"✗ Post NOT FOUND in staging database")
        print(f"\nPossible reasons:")
        print(f"  1. Crawler has not run yet for staging.awseuccontent.com")
        print(f"  2. Post date filter may be excluding future dates (2026-03-02)")
        print(f"  3. URL pattern not matching crawler configuration")
        print(f"  4. Post may be behind authentication/paywall")
        print(f"  5. Crawler may have rate limiting or error issues")
        
except Exception as e:
    print(f"✗ Error searching for specific post: {str(e)}")

print("\n" + "=" * 80)
print("CHECKING ALL BUILDER.AWS POSTS:")
print("=" * 80)

response = table.scan(
    FilterExpression='#src = :builder',
    ExpressionAttributeNames={'#src': 'source'},
    ExpressionAttributeValues={':builder': 'builder.aws.com'}
)

posts = response['Items']

# Handle pagination
while 'LastEvaluatedKey' in response:
    response = table.scan(
        FilterExpression='#src = :builder',
        ExpressionAttributeNames={'#src': 'source'},
        ExpressionAttributeValues={':builder': 'builder.aws.com'},
        ExclusiveStartKey=response['LastEvaluatedKey']
    )
    posts.extend(response['Items'])

print(f"Total posts: {len(posts)}\n")

# Check for staging.awseuccontent.com posts
print("CHECKING STAGING SOURCE POSTS:")
print("-" * 80)

staging_response = table.scan(
    FilterExpression='#src = :staging',
    ExpressionAttributeNames={'#src': 'source'},
    ExpressionAttributeValues={':staging': 'staging.awseuccontent.com'}
)

staging_posts = staging_response['Items']

# Handle pagination for staging posts
while 'LastEvaluatedKey' in staging_response:
    staging_response = table.scan(
        FilterExpression='#src = :staging',
        ExpressionAttributeNames={'#src': 'source'},
        ExpressionAttributeValues={':staging': 'staging.awseuccontent.com'},
        ExclusiveStartKey=staging_response['LastEvaluatedKey']
    )
    staging_posts.extend(staging_response['Items'])

print(f"Total staging.awseuccontent.com posts: {len(staging_posts)}")

if staging_posts:
    print("\nRecent staging posts:")
    # Sort by published_date if available
    sorted_staging = sorted(staging_posts, key=lambda x: x.get('published_date', ''), reverse=True)
    for post in sorted_staging[:5]:
        print(f"  • {post.get('title', 'No title')[:60]}")
        print(f"    Date: {post.get('published_date', 'N/A')}")
        print(f"    URL: {post.get('url', 'N/A')[:80]}")
        print()
else:
    print("✗ No posts found from staging.awseuccontent.com")
    print("  This indicates the staging crawler may not be configured or running")

# Categorize posts
with_real_authors = [p for p in posts if p.get('authors') != 'AWS Builder Community']
with_summaries = [p for p in posts if p.get('summary')]
with_labels = [p for p in posts if p.get('label')]

print("\nBUILDER.AWS STATUS BREAKDOWN:")
print("-" * 80)
print(f"✓ Posts with real authors: {len(with_real_authors)}/{len(posts)}")
print(f"✓ Posts with summaries: {len(with_summaries)}/{len(posts)}")
print(f"✓ Posts with labels: {len(with_labels)}/{len(posts)}")

if with_real_authors:
    print(f"\nSample posts with real authors:")
    for post in with_real_authors[:5]:
        print(f"  • {post.get('title', 'No title')[:60]}")
        print(f"    Author: {post.get('authors')}")
        print(f"    Summary: {'Yes' if post.get('summary') else 'No'}")
        print(f"    Label: {post.get('label', 'None')}")

if with_summaries:
    print(f"\nSample posts with summaries:")
    for post in with_summaries[:3]:
        print(f"  • {post.get('title', 'No title')[:60]}")
        print(f"    Summary: {post.get('summary', '')[:100]}...")

print("\n" + "=" * 80)
print("NEXT STEPS FOR MISSING POST:")
print("-" * 80)
print("1. Verify crawler configuration includes staging.awseuccontent.com")
print("2. Check crawler logs for errors accessing the staging domain")
print("3. Verify the post URL is accessible and not returning 404")
print("4. Check if date filter excludes future dates (2026-03-02 is future)")
print("5. Run crawler manually with staging.awseuccontent.com source")
print("6. Verify DynamoDB table permissions for crawler")

print("\n" + "=" * 80)
print("GENERAL NEXT STEPS:")
print("-" * 80)
if len(with_real_authors) < len(posts):
    print(f"  • {len(posts) - len(with_real_authors)} posts still need real authors")
    print("  • Run crawler again to process remaining posts")
if len(with_summaries) < len(with_real_authors):
    print(f"  • {len(with_real_authors) - len(with_summaries)} posts with authors need summaries")
    print("  • Check summary generator logs")
if len(with_labels) < len(with_summaries):
    print(f"  • {len(with_summaries) - len(with_labels)} posts with summaries need labels")
    print("  • Check classifier logs")
```