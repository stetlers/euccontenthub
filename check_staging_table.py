```python
#!/usr/bin/env python3
"""Check what's in the staging table and debug crawler issues"""

import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
import json

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

def check_posts_by_date_range(start_date, end_date):
    """Check for posts published within a date range"""
    try:
        response = table.scan(
            FilterExpression='date_published BETWEEN :start AND :end',
            ExpressionAttributeValues={
                ':start': start_date,
                ':end': end_date
            }
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error checking posts by date range: {e}")
        return []

def check_posts_by_url_pattern(url_pattern):
    """Search for posts by URL pattern"""
    try:
        response = table.scan(
            FilterExpression='contains(#url, :pattern)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':pattern': url_pattern}
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error searching by URL pattern: {e}")
        return []

def analyze_date_distribution(all_posts):
    """Analyze the distribution of posts by date to identify gaps"""
    date_counts = {}
    for post in all_posts:
        date = post.get('date_published', 'Unknown')
        date_counts[date] = date_counts.get(date, 0) + 1
    
    return dict(sorted(date_counts.items(), reverse=True))

def check_crawler_metadata():
    """Check for crawler metadata or state information"""
    try:
        # Look for any metadata entries (if crawler stores state)
        response = table.scan(
            FilterExpression='attribute_exists(crawler_run_timestamp) OR attribute_exists(last_crawled)',
            Limit=10
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Note: No crawler metadata found (this may be expected): {e}")
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
    
    # Get all posts for comprehensive analysis
    response = table.scan()
    all_posts = response.get('Items', [])
    
    # Handle pagination if there are more items
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        all_posts.extend(response.get('Items', []))
    
    # Count by source
    aws_blog_count = sum(1 for p in all_posts if 'aws.amazon.com' in p.get('source', ''))
    builder_count = sum(1 for p in all_posts if 'builder.aws.com' in p.get('source', ''))
    
    print(f"Posts by source:")
    print(f"  AWS Blog: {aws_blog_count}")
    print(f"  Builder.AWS: {builder_count}")
    
    # Debug: Check for the specific missing post
    print("\n" + "="*80)
    print("DEBUGGING: Checking for missing post")
    print("Target: 'Amazon WorkSpaces launches Graphics G6, Gr6, and G6f bundles'")
    print("Expected Date: March 2, 2026 (2026-03-02)")
    print("="*80)
    
    # Search by title variations
    search_variations = [
        "WorkSpaces launches Graphics",
        "WorkSpaces Graphics G6",
        "Graphics G6",
        "Gr6",
        "G6f bundles",
        "WorkSpaces"
    ]
    
    print(f"\nSearching by title variations...")
    all_matches = []
    for search_title in search_variations:
        matching_posts = check_specific_post(search_title)
        if matching_posts:
            all_matches.extend(matching_posts)
            print(f"  ✓ Found {len(matching_posts)} match(es) for '{search_title}'")
    
    # Deduplicate matches
    unique_matches = {post.get('post_id'): post for post in all_matches}.values()
    
    if unique_matches:
        print(f"\nTotal unique matching post(s): {len(unique_matches)}")
        for post in unique_matches:
            print(f"  - {post.get('title')}")
            print(f"    ID: {post.get('post_id')}")
            print(f"    Source: {post.get('source')}")
            print(f"    Date: {post.get('date_published')}")
            print(f"    URL: {post.get('url', 'N/A')}")
            print(f"    Crawled at: {post.get('crawled_timestamp', 'N/A')}")
    else:
        print("  ❌ No posts found matching any title variation")
    
    # Search by URL pattern for WorkSpaces
    print(f"\nSearching by URL pattern (workspaces)...")
    workspaces_posts = check_posts_by_url_pattern('workspaces')
    if workspaces_posts:
        print(f"  Found {len(workspaces_posts)} post(s) with 'workspaces' in URL:")
        for post in workspaces_posts[:5]:
            print(f"    - [{post.get('date_published')}] {post.get('title', 'No title')[:60]}...")
    else:
        print("  ❌ No posts found with 'workspaces' in URL")
    
    # Check for posts on March 2, 2026
    target_date = '2026-03-02'
    print(f"\nChecking for posts published on {target_date}...")
    posts_on_date = check_posts_by_date(target_date)
    
    if posts_on_date:
        print(f"Found {len(posts_on_date)} post(s) on {target_date}:")
        for post in posts_on_date:
            print(f"  - {post.get('title', 'No title')}")
            print(f"    Source: {post.get('source', 'Unknown')}")
            print(f"    URL: {post.get('url', 'N/A')}")
    else:
        print(f"  ❌ No posts found on {target_date}")
    
    # Check for posts in March 2026
    print(f"\nChecking for posts in March 2026 (2026-03-01 to 2026-03-31)...")
    march_2026_posts = check_posts_by_date_range('2026-03-01', '2026-03-31')
    
    if march_2026_posts:
        print(f"Found {len(march_2026_posts)} post(s) in March 2026:")
        for post in sorted(march_2026_posts, key=lambda x: x.get('date_published', '')):
            print(f"  - [{post.get('date_published')}] {post.get('title', 'No title')[:60]}...")
    else:
        print(f"  ❌ No posts found in March 2026")
    
    # Check recent posts (last 7 days from now)
    print(f"\nChecking for posts in the last 7 days from today ({datetime.now().strftime('%Y-%m-%d')})...")
    recent_posts = check_recent_posts(days=7)
    
    if recent_posts:
        print(f"Found {len(recent_posts)} recent post(s):")
        for post in sorted(recent_posts, key=lambda x: x.get('date_published', ''), reverse=True)[:10]:
            print(f"  - [{post.get('date_published')}] {post.get('title', 'No title')[:60]}...")
    else:
        print("  ❌ No recent posts found in the last 7 days")
    
    # Check for future dates (crawler date filtering issue)
    print(f"\nChecking for posts with future dates (beyond {datetime.now().strftime('%Y-%m-%d')})...")
    future_posts = [p for p in all_posts if p.get('date_published', '') > datetime.now().strftime('%Y-%m-%d')]
    
    if future_posts:
        print(f"⚠️  WARNING: Found {len(future_posts)} post(s) with future dates:")
        for post in sorted(future_posts, key=lambda x: x.get('date_published', ''), reverse=True)[:10]:
            print(f"  - [{post.get('date_published')}] {post.get('title', 'No title')[:60]}...")
            print(f"    URL: {post.get('url', 'N/A')}")
        print("\n  ⚠️  POTENTIAL ISSUE: Future dates detected!")
        print("     This suggests the crawler may be filtering out posts with dates > today")
        print("     OR there's a date parsing issue")
    else:
        print("  ✓ No posts with future dates found")
        print("  ⚠️  CRITICAL: If the missing post is dated 2026-03-02, it may be filtered out!")
    
    # Analyze date distribution
    print(f"\n" + "="*80)
    print("Date Distribution Analysis (showing dates with most posts):")
    print("="*80)
    date_distribution = analyze_date_distribution(all_posts)
    for date, count in list(date_distribution.items())[:15]:
        print(f"  {date}: {count} post(s)")
    
    # Check for date gaps
    if all_posts:
        all_dates = sorted([p.get('date_published', '') for p in all_posts if p.get('date_published')])
        if all_dates:
            earliest_date = all_dates[0]
            latest_date = all_dates[-1]
            print(f"\nDate range in table: {earliest_date} to {latest_date}")
            
            # Check if target date falls within range
            if earliest_date <= target_date <= latest_date:
                print(f"  ⚠️  Target date {target_date} is WITHIN the range but post is missing!")
                print("     This suggests a crawler filtering or URL detection issue")
            elif target_date > latest_date:
                print(f"  ⚠️  Target date {target_date} is AFTER the latest crawled date!")
                print("     This suggests the crawler hasn't run recently or is filtering future dates")
            else:
                print(f"  ℹ️  Target date {target_date} is BEFORE the earliest crawled date")
    
    # Check crawler metadata
    print(f"\n" + "="*80)
    print("Crawler Metadata Check:")
    print("="*80)
    metadata = check_crawler_metadata()
    if metadata:
        print(f"Found {len(metadata)} item(s) with crawler metadata:")
        for item in metadata[:5]:
            print(f"  - {json.dumps(item, default=str, indent=4)}")
    else:
        print("  No crawler metadata found in table")
    
    # Summary of latest posts
    print(f"\n" + "="*80)
    print("Latest 10 posts by publication date:")
    print("="*80)
    sorted_posts = sorted(all_posts, key=lambda x: x.get('date_published', ''), reverse=True)[:10]
    for post in sorted_posts:
        print(f"  [{post.get('date_published')}] {post.get('title', 'No title')[:60]}...")
        print(f"    Source: {post.get('source', 'Unknown')}")
        print(f"    URL: {post.get('url', 'N/A')}")
    
    # Check for staging.awseuccontent.com in sources
    print(f"\n" + "="*80)
    print("Staging Domain Check:")
    print("="*80)
    staging_posts = [p for p in all_posts if 'staging.awseuccontent.com' in p.get('source', '') or 'staging.awseuccontent.com' in p.get('url', '')]
    if staging_posts:
        print(f"  Found {len(staging_posts)} post(s) from staging.awseuccontent.com")
        for post in staging_posts[:5]:
            print(f"    - [{post.get('date_published')}] {post.get('title', 'No title')[:60]}...")
    else:
        print("  ❌ No posts found from staging.awseuccontent.com domain")
        print("  ⚠️  CRITICAL: Crawler may not be accessing the staging domain!")
    
    print("\n" + "="*80)
    print("DIAGNOSTIC SUMMARY:")
    print("="*80)
    print(f"✓ Total posts in table: {total_count}")
    print(f"{'✓' if future_posts else '❌'} Future-dated posts found: {len(future_posts)}")
    print(f"{'❌' if not posts_on_date else '✓'} Post found on target date (2026-03-02): {len(posts_on_date)}")
    print(f"{'❌' if not unique_matches else '✓'} Post found by title search: {len(unique_matches)}")
    print(f"{'❌' if not staging_posts else '✓'} Posts from staging domain: {len(staging_posts)}")
    
    print("\n" + "="*80)
    print("NEXT STEPS FOR DEBUGGING:")
    print("="*80)
    print("1. ⚠️  CHECK CRAWLER DATE FILTERING:")
    print("   - Verify if crawler filters out posts with date > current date")
    print("   - Target post is dated 2026-03-02 (future date)")
    print("