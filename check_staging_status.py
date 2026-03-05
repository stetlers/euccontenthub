```python
"""
Check detailed status of Builder.AWS posts in staging and investigate missing posts
"""
import boto3
from datetime import datetime, timedelta
import feedparser
from bs4 import BeautifulSoup
import requests

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
staging_table = dynamodb.Table('aws-blog-posts-staging')
production_table = dynamodb.Table('aws-blog-posts')

print("Checking Builder.AWS posts status in staging...")
print("=" * 80)

# Scan staging posts
response = staging_table.scan(
    FilterExpression='#src = :builder',
    ExpressionAttributeNames={'#src': 'source'},
    ExpressionAttributeValues={':builder': 'builder.aws.com'}
)

staging_posts = response['Items']

# Handle pagination for staging
while 'LastEvaluatedKey' in response:
    response = staging_table.scan(
        FilterExpression='#src = :builder',
        ExpressionAttributeNames={'#src': 'source'},
        ExpressionAttributeValues={':builder': 'builder.aws.com'},
        ExclusiveStartKey=response['LastEvaluatedKey']
    )
    staging_posts.extend(response['Items'])

print(f"Total posts in staging: {len(staging_posts)}\n")

# Categorize posts
with_real_authors = [p for p in staging_posts if p.get('authors') != 'AWS Builder Community']
with_summaries = [p for p in staging_posts if p.get('summary')]
with_labels = [p for p in staging_posts if p.get('label')]

print("STATUS BREAKDOWN:")
print("-" * 80)
print(f"✓ Posts with real authors: {len(with_real_authors)}/{len(staging_posts)}")
print(f"✓ Posts with summaries: {len(with_summaries)}/{len(staging_posts)}")
print(f"✓ Posts with labels: {len(with_labels)}/{len(staging_posts)}")

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

# NEW: Investigation section for missing March 2, 2026 post
print("\nINVESTIGATING MISSING POST: Amazon WorkSpaces Graphics G6 bundles (March 2, 2026)")
print("=" * 80)

# Check if the post exists in production
production_response = production_table.scan(
    FilterExpression='#src = :builder',
    ExpressionAttributeNames={'#src': 'source'},
    ExpressionAttributeValues={':builder': 'builder.aws.com'}
)

production_posts = production_response['Items']

# Handle pagination for production
while 'LastEvaluatedKey' in production_response:
    production_response = production_table.scan(
        FilterExpression='#src = :builder',
        ExpressionAttributeNames={'#src': 'source'},
        ExpressionAttributeValues={':builder': 'builder.aws.com'},
        ExclusiveStartKey=production_response['LastEvaluatedKey']
    )
    production_posts.extend(production_response['Items'])

print(f"Total posts in production: {len(production_posts)}")

# Look for the specific post
target_keywords = ['workspaces', 'graphics', 'g6', 'bundles']
target_date = '2026-03-02'

print(f"\nSearching for posts matching keywords: {target_keywords}")
print(f"Target date: {target_date}\n")

# Check staging
print("STAGING TABLE:")
matching_staging = []
for post in staging_posts:
    title = post.get('title', '').lower()
    pub_date = post.get('publishedDate', '')
    if any(keyword in title for keyword in target_keywords) and target_date in pub_date:
        matching_staging.append(post)
        
if matching_staging:
    for post in matching_staging:
        print(f"  ✓ FOUND: {post.get('title')}")
        print(f"    Date: {post.get('publishedDate')}")
        print(f"    URL: {post.get('url')}")
        print(f"    Authors: {post.get('authors')}")
else:
    print("  ✗ NOT FOUND in staging")

# Check production
print("\nPRODUCTION TABLE:")
matching_production = []
for post in production_posts:
    title = post.get('title', '').lower()
    pub_date = post.get('publishedDate', '')
    if any(keyword in title for keyword in target_keywords) and target_date in pub_date:
        matching_production.append(post)

if matching_production:
    for post in matching_production:
        print(f"  ✓ FOUND: {post.get('title')}")
        print(f"    Date: {post.get('publishedDate')}")
        print(f"    URL: {post.get('url')}")
        print(f"    Authors: {post.get('authors')}")
else:
    print("  ✗ NOT FOUND in production")

# Check the RSS feed directly
print("\nCHECKING RSS FEED DIRECTLY:")
print("-" * 80)
try:
    feed_url = 'https://builder.aws.com/feed'
    feed = feedparser.parse(feed_url)
    
    print(f"Feed entries found: {len(feed.entries)}")
    
    feed_matches = []
    for entry in feed.entries:
        title = entry.get('title', '').lower()
        pub_date = entry.get('published', '')
        
        # Parse the date from the entry
        try:
            entry_date = datetime(*entry.published_parsed[:6])
            entry_date_str = entry_date.strftime('%Y-%m-%d')
        except:
            entry_date_str = ''
        
        if any(keyword in title for keyword in target_keywords):
            feed_matches.append({
                'title': entry.get('title'),
                'date': entry_date_str,
                'url': entry.get('link'),
                'published': pub_date
            })
    
    if feed_matches:
        print("\nMatching posts in RSS feed:")
        for match in feed_matches:
            print(f"  • {match['title']}")
            print(f"    Date: {match['date']}")
            print(f"    URL: {match['url']}")
            print(f"    Match target date: {'YES' if target_date in match['date'] else 'NO'}")
            print()
    else:
        print("  ✗ No matching posts found in RSS feed")
    
    # Check date range of feed entries
    print("\nFeed date range analysis:")
    dates = []
    for entry in feed.entries:
        try:
            entry_date = datetime(*entry.published_parsed[:6])
            dates.append(entry_date)
        except:
            pass
    
    if dates:
        dates.sort()
        print(f"  Oldest post: {dates[0].strftime('%Y-%m-%d')}")
        print(f"  Newest post: {dates[-1].strftime('%Y-%m-%d')}")
        print(f"  Target date ({target_date}) in range: {dates[0] <= datetime(2026, 3, 2) <= dates[-1]}")
        
        # Check how many posts are from March 2026
        march_2026_posts = [d for d in dates if d.year == 2026 and d.month == 3]
        print(f"  Posts from March 2026: {len(march_2026_posts)}")
        
except Exception as e:
    print(f"  ✗ Error fetching RSS feed: {str(e)}")

# Date filtering analysis
print("\n" + "=" * 80)
print("DATE FILTERING ANALYSIS:")
print("-" * 80)

# Check staging posts date distribution
staging_dates = []
for post in staging_posts:
    pub_date = post.get('publishedDate', '')
    if pub_date:
        try:
            post_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
            staging_dates.append(post_date)
        except:
            pass

if staging_dates:
    staging_dates.sort()
    print(f"Staging date range:")
    print(f"  Oldest: {staging_dates[0].strftime('%Y-%m-%d')}")
    print(f"  Newest: {staging_dates[-1].strftime('%Y-%m-%d')}")
    
    # Check if target date would be filtered out
    target_dt = datetime(2026, 3, 2)
    if target_dt < staging_dates[0]:
        print(f"  ⚠ Target date {target_date} is BEFORE oldest staging post - may be filtered!")
    elif target_dt > staging_dates[-1]:
        print(f"  ⚠ Target date {target_date} is AFTER newest staging post - may be filtered!")
    else:
        print(f"  ✓ Target date {target_date} is within staging range")

print("\n" + "=" * 80)
print("NEXT STEPS:")
if not matching_staging and matching_production:
    print("  ⚠ POST EXISTS IN PRODUCTION BUT NOT STAGING")
    print("  • Check crawler date filtering logic")
    print("  • Verify staging crawler is processing recent posts")
    print("  • Check for URL pattern exclusions")
elif not matching_staging and not matching_production and feed_matches:
    print("  ⚠ POST EXISTS IN RSS FEED BUT NOT IN ANY TABLE")
    print("  • Verify crawler is fetching from RSS feed correctly")
    print("  • Check for date parsing issues")
    print("  • Check for URL validation logic that might exclude this post")
elif not matching_staging and not matching_production and not feed_matches:
    print("  ⚠ POST NOT FOUND IN RSS FEED")
    print("  • Post may not be published yet or has been removed")
    print("  • Verify the correct publication date")
    print("  • Check if post URL is accessible")
else:
    print("Post investigation complete. Check results above.")

if len(with_real_authors) < len(staging_posts):
    print(f"  • {len(staging_posts) - len(with_real_authors)} posts still need real authors")
    print("  • Run crawler again to process remaining posts")
if len(with_summaries) < len(with_real_authors):
    print(f"  • {len(with_real_authors) - len(with_summaries)} posts with authors need summaries")
    print("  • Check summary generator logs")
if len(with_labels) < len(with_summaries):
    print(f"  • {len(with_summaries) - len(with_labels)} posts with summaries need labels")
    print("  • Check classifier logs")
```