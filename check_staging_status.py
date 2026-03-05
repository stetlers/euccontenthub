```python
"""
Check detailed status of Builder.AWS posts in staging
"""
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("Checking Builder.AWS posts status in staging...")
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

# Categorize posts
with_real_authors = [p for p in posts if p.get('authors') != 'AWS Builder Community']
with_summaries = [p for p in posts if p.get('summary')]
with_labels = [p for p in posts if p.get('label')]

print("STATUS BREAKDOWN:")
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

# ============================================================================
# NEW: Check for specific missing post (Amazon WorkSpaces Graphics G6 bundles)
# ============================================================================
print("\n" + "=" * 80)
print("CHECKING FOR SPECIFIC POST: Amazon WorkSpaces Graphics G6 bundles")
print("-" * 80)

# Search for the specific post by title keywords
workspaces_posts = [
    p for p in posts 
    if 'workspaces' in p.get('title', '').lower() and 
       ('g6' in p.get('title', '').lower() or 'graphics' in p.get('title', '').lower())
]

if workspaces_posts:
    print(f"✓ Found {len(workspaces_posts)} WorkSpaces G6 related post(s):")
    for post in workspaces_posts:
        print(f"  • Title: {post.get('title')}")
        print(f"    URL: {post.get('url', 'N/A')}")
        print(f"    Published: {post.get('published_date', 'N/A')}")
        print(f"    Crawled: {post.get('crawled_at', 'N/A')}")
else:
    print("✗ WorkSpaces Graphics G6 bundles post NOT FOUND in staging")
    print("\nPossible reasons:")
    print("  1. Date filtering: Crawler may not be checking recent dates (March 2, 2026)")
    print("  2. URL detection: Post URL might not match crawler's URL pattern")
    print("  3. Scraping pattern: Post structure may differ from expected format")
    print("  4. Crawler frequency: Last crawl may have been before publication")

# ============================================================================
# NEW: Analyze post date distribution to detect date filtering issues
# ============================================================================
print("\n" + "=" * 80)
print("POST DATE DISTRIBUTION ANALYSIS:")
print("-" * 80)

posts_with_dates = [p for p in posts if p.get('published_date')]
if posts_with_dates:
    # Sort posts by date
    sorted_posts = sorted(posts_with_dates, key=lambda x: x.get('published_date', ''), reverse=True)
    
    print(f"\nMost recent posts (top 10):")
    for post in sorted_posts[:10]:
        pub_date = post.get('published_date', 'N/A')
        print(f"  • {pub_date}: {post.get('title', 'No title')[:60]}")
    
    # Check if there are posts from March 2026
    target_date = "2026-03"
    march_2026_posts = [p for p in posts if p.get('published_date', '').startswith(target_date)]
    
    if march_2026_posts:
        print(f"\n✓ Found {len(march_2026_posts)} post(s) from March 2026")
    else:
        print(f"\n✗ No posts found from March 2026")
        print("  → This suggests the crawler's date filtering may be blocking recent posts")
        
        # Check latest date in database
        if sorted_posts:
            latest_date = sorted_posts[0].get('published_date', 'Unknown')
            print(f"  → Latest post date in staging: {latest_date}")
            
            # Check if latest date is before target
            if latest_date < target_date:
                print(f"  → WARNING: Latest post is older than March 2, 2026")
                print(f"  → ACTION REQUIRED: Check crawler date range configuration")
    
    # Check for recent crawl activity
    posts_with_crawl_time = [p for p in posts if p.get('crawled_at')]
    if posts_with_crawl_time:
        recent_crawls = sorted(
            posts_with_crawl_time, 
            key=lambda x: x.get('crawled_at', ''), 
            reverse=True
        )[:5]
        
        print(f"\nMost recent crawler activity (top 5):")
        for post in recent_crawls:
            crawl_time = post.get('crawled_at', 'N/A')
            print(f"  • Crawled at {crawl_time}: {post.get('title', 'No title')[:50]}")
else:
    print("✗ No posts with published_date field found")
    print("  → This indicates a data structure issue with the crawler")

# ============================================================================
# NEW: Check for URL pattern issues
# ============================================================================
print("\n" + "=" * 80)
print("URL PATTERN ANALYSIS:")
print("-" * 80)

url_patterns = {}
for post in posts:
    url = post.get('url', '')
    if url:
        # Extract URL pattern (path structure)
        parts = url.split('/')
        if len(parts) >= 4:
            pattern = '/'.join(parts[:4]) + '/...'
            url_patterns[pattern] = url_patterns.get(pattern, 0) + 1

if url_patterns:
    print("\nDetected URL patterns:")
    for pattern, count in sorted(url_patterns.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {pattern} ({count} posts)")
    
    print("\nACTION: Verify the WorkSpaces G6 post URL matches these patterns")
else:
    print("✗ No URL patterns detected")
    print("  → This suggests posts may not have URL field populated")

print("\n" + "=" * 80)
print("NEXT STEPS:")
if len(with_real_authors) < len(posts):
    print(f"  • {len(posts) - len(with_real_authors)} posts still need real authors")
    print("  • Run crawler again to process remaining posts")
if len(with_summaries) < len(with_real_authors):
    print(f"  • {len(with_real_authors) - len(with_summaries)} posts with authors need summaries")
    print("  • Check summary generator logs")
if len(with_labels) < len(with_summaries):
    print(f"  • {len(with_summaries) - len(with_labels)} posts with summaries need labels")
    print("  • Check classifier logs")

# Add specific actions for missing post investigation
if not workspaces_posts:
    print("\nSPECIFIC ACTIONS FOR MISSING POST:")
    print("  1. Verify post is published at source: https://builder.aws.com")
    print("  2. Check crawler logs for date range being scanned")
    print("  3. Manually test URL scraping pattern against the WorkSpaces G6 post")
    print("  4. Ensure crawler is running and not rate-limited")
    print("  5. Check if post is behind authentication or geo-restriction")
    print("  6. Review crawler's RSS/sitemap feed parsing logic")
    print("  7. Verify DynamoDB write permissions and error handling")
```