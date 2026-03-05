```python
"""
Check detailed status of Builder.AWS posts in staging
"""
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr

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

# New detection logic: Check for specific missing post
print("\n" + "=" * 80)
print("CHECKING FOR SPECIFIC POST:")
print("-" * 80)

# Search for the reported missing post about Amazon WorkSpaces
target_keywords = ['Amazon WorkSpaces', 'Graphics G6', 'Gr6', 'G6f']
target_date = '2026-03-02'

missing_post_found = False
for post in posts:
    title = post.get('title', '')
    pub_date = post.get('published_date', '')
    
    # Check if this is the target post
    if any(keyword.lower() in title.lower() for keyword in target_keywords):
        if target_date in pub_date:
            missing_post_found = True
            print(f"✓ Target post FOUND in staging:")
            print(f"  Title: {title}")
            print(f"  Date: {pub_date}")
            print(f"  Authors: {post.get('authors', 'N/A')}")
            print(f"  URL: {post.get('url', 'N/A')}")
            break

if not missing_post_found:
    print(f"✗ Target post NOT FOUND in staging:")
    print(f"  Expected: Post about 'Amazon WorkSpaces launches Graphics G6, Gr6, and G6f bundles'")
    print(f"  Expected Date: {target_date}")
    print(f"  Action Required: Investigate crawler logs and RSS feed")

# Check for recent posts around the target date
print(f"\nPosts from March 2026:")
march_2026_posts = [p for p in posts if p.get('published_date', '').startswith('2026-03')]
if march_2026_posts:
    # Sort by date
    march_2026_posts.sort(key=lambda x: x.get('published_date', ''), reverse=True)
    for post in march_2026_posts[:10]:
        print(f"  • [{post.get('published_date', 'No date')}] {post.get('title', 'No title')[:70]}")
else:
    print("  No posts found from March 2026")

# Analyze date coverage to identify gaps
print(f"\nDate Coverage Analysis:")
if posts:
    dates_with_posts = set()
    for post in posts:
        pub_date = post.get('published_date', '')
        if pub_date:
            # Extract date only (YYYY-MM-DD)
            date_only = pub_date.split('T')[0] if 'T' in pub_date else pub_date[:10]
            dates_with_posts.add(date_only)
    
    # Check if target date has any posts
    if target_date in dates_with_posts:
        same_day_posts = [p for p in posts if target_date in p.get('published_date', '')]
        print(f"  • {target_date}: {len(same_day_posts)} post(s) found")
        for post in same_day_posts:
            print(f"    - {post.get('title', 'No title')[:70]}")
    else:
        print(f"  • {target_date}: NO posts found (POTENTIAL GAP)")
        print(f"    This suggests the crawler may have missed posts on this date")
    
    # Show recent dates with post counts
    sorted_dates = sorted(dates_with_posts, reverse=True)
    print(f"\n  Recent dates with posts:")
    for date in sorted_dates[:10]:
        count = len([p for p in posts if date in p.get('published_date', '')])
        print(f"    {date}: {count} post(s)")

print("\n" + "=" * 80)
print("NEXT STEPS:")
if not missing_post_found:
    print("  ⚠ MISSING POST DETECTED:")
    print(f"    1. Verify the post exists at builder.aws.com with date {target_date}")
    print("    2. Check crawler RSS feed URL and date filtering logic")
    print("    3. Review crawler logs for any errors on or around this date")
    print("    4. Verify crawler's date parsing handles timezone correctly")
    print("    5. Run manual crawl for date range: 2026-03-01 to 2026-03-03")
    print("    6. Check if RSS feed pagination is working correctly")
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