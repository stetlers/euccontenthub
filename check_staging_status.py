```python
"""
Check detailed status of Builder.AWS posts in staging
Enhanced with WorkSpaces Graphics G6 bundles investigation diagnostics
"""
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
import re

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
# ENHANCED: Check for specific missing post (Amazon WorkSpaces Graphics G6 bundles)
# ============================================================================
print("\n" + "=" * 80)
print("CHECKING FOR SPECIFIC POST: Amazon WorkSpaces Graphics G6 bundles")
print("Expected Publication Date: March 2, 2026")
print("-" * 80)

# Search for the specific post by title keywords (multiple variations)
workspaces_keywords = ['workspaces', 'workspace']
g6_keywords = ['g6', 'gr6', 'g6f', 'graphics g6', 'graphics bundles']

workspaces_posts = []
for post in posts:
    title_lower = post.get('title', '').lower()
    # Check for WorkSpaces AND any G6 variant
    if any(kw in title_lower for kw in workspaces_keywords):
        if any(kw in title_lower for kw in g6_keywords):
            workspaces_posts.append(post)

if workspaces_posts:
    print(f"✓ Found {len(workspaces_posts)} WorkSpaces G6 related post(s):")
    for post in workspaces_posts:
        print(f"  • Title: {post.get('title')}")
        print(f"    URL: {post.get('url', 'N/A')}")
        print(f"    Published: {post.get('published_date', 'N/A')}")
        print(f"    Crawled: {post.get('crawled_at', 'N/A')}")
        print(f"    Source: {post.get('source', 'N/A')}")
        print(f"    ID: {post.get('id', 'N/A')}")
else:
    print("✗ WorkSpaces Graphics G6 bundles post NOT FOUND in staging")
    print("\nTROUBLESHOOTING CHECKLIST:")
    print("  1. Date filtering: Crawler may not be checking March 2026 dates")
    print("  2. URL detection: Post URL might not match crawler's URL pattern")
    print("  3. Scraping pattern: Post structure may differ from expected format")
    print("  4. Crawler frequency: Last crawl may have been before March 2, 2026")
    print("  5. Source filtering: Post may be from aws.amazon.com not builder.aws.com")
    print("  6. Rate limiting: Crawler may have been throttled during March 2 window")
    print("  7. Storage failures: Post may have been scraped but not written to DynamoDB")

# ============================================================================
# ENHANCED: Check all sources for the missing post
# ============================================================================
print("\n" + "=" * 80)
print("CHECKING ALL SOURCES FOR WORKSPACES G6 POST:")
print("-" * 80)

try:
    # Scan all posts regardless of source
    all_sources_response = table.scan()
    all_posts = all_sources_response['Items']
    
    while 'LastEvaluatedKey' in all_sources_response:
        all_sources_response = table.scan(
            ExclusiveStartKey=all_sources_response['LastEvaluatedKey']
        )
        all_posts.extend(all_sources_response['Items'])
    
    # Search across all sources
    all_workspaces_posts = []
    for post in all_posts:
        title_lower = post.get('title', '').lower()
        if any(kw in title_lower for kw in workspaces_keywords):
            if any(kw in title_lower for kw in g6_keywords):
                all_workspaces_posts.append(post)
    
    if all_workspaces_posts:
        print(f"✓ Found {len(all_workspaces_posts)} WorkSpaces G6 post(s) across ALL sources:")
        for post in all_workspaces_posts:
            print(f"  • Title: {post.get('title')}")
            print(f"    Source: {post.get('source', 'N/A')}")
            print(f"    URL: {post.get('url', 'N/A')}")
            print(f"    Published: {post.get('published_date', 'N/A')}")
            print(f"    Crawled: {post.get('crawled_at', 'N/A')}")
            print()
    else:
        print("✗ WorkSpaces G6 post NOT FOUND in ANY source")
        print("  → This confirms the post has not been crawled at all")
        print("  → Primary issue is likely with crawler URL discovery or date filtering")
        
    # Show source distribution
    sources = {}
    for post in all_posts:
        src = post.get('source', 'unknown')
        sources[src] = sources.get(src, 0) + 1
    
    print("\nAll sources in staging database:")
    for src, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {src}: {count} posts")

except Exception as e:
    print(f"✗ Error scanning all sources: {str(e)}")

# ============================================================================
# ENHANCED: Analyze post date distribution to detect date filtering issues
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
    
    # Check date range coverage
    oldest_date = sorted_posts[-1].get('published_date', 'Unknown')
    newest_date = sorted_posts[0].get('published_date', 'Unknown')
    
    print(f"\nDate range in database:")
    print(f"  Oldest: {oldest_date}")
    print(f"  Newest: {newest_date}")
    
    # Check if there are posts from March 2026
    target_date = "2026-03-02"
    target_month = "2026-03"
    
    exact_match_posts = [p for p in posts if p.get('published_date', '').startswith(target_date)]
    march_2026_posts = [p for p in posts if p.get('published_date', '').startswith(target_month)]
    
    if exact_match_posts:
        print(f"\n✓ Found {len(exact_match_posts)} post(s) from March 2, 2026:")
        for post in exact_match_posts:
            print(f"  • {post.get('title', 'No title')[:70]}")
    else:
        print(f"\n✗ No posts found from March 2, 2026")
    
    if march_2026_posts:
        print(f"\n✓ Found {len(march_2026_posts)} post(s) from March 2026")
        print(f"  Sample titles:")
        for post in march_2026_posts[:5]:
            print(f"  • {post.get('published_date')}: {post.get('title', 'No title')[:60]}")
    else:
        print(f"\n✗ No posts found from March 2026")
        print("  → CRITICAL: This suggests the crawler's date filtering is blocking March 2026 posts")
        
        # Check if we're getting ANY recent posts
        if newest_date < target_date:
            print(f"  → ERROR: Latest post ({newest_date}) is older than target date ({target_date})")
            print(f"  → ACTION REQUIRED: Check crawler date range configuration")
            print(f"  → LIKELY CAUSE: Hardcoded date limit or lookback window too short")
        elif newest_date > target_date:
            print(f"  → Latest post ({newest_date}) is AFTER target date")
            print(f"  → This means crawler IS processing March 2026, but specific post is missing")
            print(f"  → LIKELY CAUSE: URL not discovered or scraping pattern mismatch")
    
    # Analyze date gaps
    print(f"\nChecking for date gaps around target date:")
    dates_around_target = [
        p for p in posts 
        if '2026-02-25' <= p.get('published_date', '') <= '2026-03-10'
    ]
    if dates_around_target:
        sorted_around = sorted(dates_around_target, key=lambda x: x.get('published_date', ''))
        print(f"  Found {len(dates_around_target)} posts between Feb 25 - Mar 10, 2026:")
        for post in sorted_around:
            print(f"  • {post.get('published_date')}: {post.get('title', 'No title')[:60]}")
    else:
        print(f"  ✗ No posts found in Feb 25 - Mar 10, 2026 range")
        print(f"  → This indicates a crawler outage or date filtering issue during this period")
    
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
            pub_date = post.get('published_date', 'N/A')
            print(f"  • Crawled at {crawl_time} (pub: {pub_date})")
            print(f"    {post.get('title', 'No title')[:60]}")
        
        # Calculate crawler lag
        latest_crawl = recent_crawls[0].get('crawled_at', '')
        if latest_crawl:
            print(f"\n  Latest crawl timestamp: {latest_crawl}")
            print(f"  Target post date: {target_date}")
            if latest_crawl < target_date:
                print(f"  → WARNING: Crawler hasn't run since target post was published")
    else:
        print("\n✗ No crawled_at timestamps found")
        print("  → This indicates crawler metadata is not being stored properly")
else:
    print("✗ No posts with published_date field found")
    print("  → This indicates a critical data structure issue with the crawler")

# ============================================================================
# ENHANCED: Check for URL pattern issues
# ============================================================================
print("\n" + "=" * 80)
print("URL PATTERN ANALYSIS:")
print("-" * 80)

url_patterns = {}
url_domains = {}
for post in posts:
    url = post.get('url', '')
    if url:
        # Extract domain
        domain_match = re.match(r'https?://([^/]+)', url)
        if domain_match:
            domain = domain_match.group(1)
            url_domains[domain] = url_domains.get(domain, 0) + 1
        
        # Extract URL pattern (path structure)
        parts = url.split('/')
        if len(parts) >= 4:
            pattern = '/'.join(parts[:4]) + '/...'
            url_patterns[pattern] = url_patterns.get(pattern, 0) + 1

if url_domains:
    print("\nDetected domains:")
    for domain, count in sorted(url_domains.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {domain} ({count} posts)")

if url_patterns:
    print("\nDetected URL patterns:")
    for pattern, count in sorted(url_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  • {pattern} ({count} posts)")
    
    print("\nExpected URL for WorkSpaces G6 post:")
    print("  • Should match: https://aws.amazon.com/blogs/aws/...")
    print("  • Or: https://aws.amazon.com/blogs/desktop-and-application-streaming/...")
    print("  ACTION: Verify the actual post URL matches these patterns")
else:
    print("✗ No URL patterns detected")
    print("  → This suggests posts may not have URL field populated")

# Sample some URLs for pattern verification
print("\nSample URLs from database (first 5):")
sample_urls = [p.get('url') for p in posts[:5] if p.get('url')]
for url in sample_urls:
    print(f"  • {url}")

# ============================================================================
# NEW: Check for posts with similar titles (near-matches)
# ============================================================================
print("\n" + "=" * 80)
print("CHECKING FOR SIMILAR POST TITLES:")
print("-" * 80)

workspaces_related = [
    p for p in posts 
    if 'workspaces' in p.get('title', '').lower()
]

if workspaces_related:
    print(f"\nFound {len(workspaces_related)} Work