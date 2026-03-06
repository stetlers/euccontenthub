```python
#!/usr/bin/env python3
"""Check what's in the staging table and debug crawler issues"""

import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
import json
import sys

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

def check_all_attributes(all_posts):
    """Analyze all attributes present in posts to understand data structure"""
    all_attributes = set()
    attribute_examples = {}
    
    for post in all_posts[:100]:  # Sample first 100 posts
        for key, value in post.items():
            all_attributes.add(key)
            if key not in attribute_examples:
                attribute_examples[key] = str(value)[:100]
    
    return sorted(list(all_attributes)), attribute_examples

def check_url_in_all_fields(target_keyword):
    """Search for a keyword across all text fields in posts"""
    try:
        response = table.scan()
        all_posts = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            all_posts.extend(response.get('Items', []))
        
        matches = []
        for post in all_posts:
            # Search in all string fields
            for key, value in post.items():
                if isinstance(value, str) and target_keyword.lower() in value.lower():
                    matches.append(post)
                    break
        
        return matches
    except ClientError as e:
        print(f"Error in comprehensive search: {e}")
        return []

def analyze_source_patterns(all_posts):
    """Analyze source URL patterns to identify crawler coverage"""
    source_domains = {}
    for post in all_posts:
        source = post.get('source', 'Unknown')
        url = post.get('url', '')
        
        # Extract domain from source or URL
        domain = 'Unknown'
        if source != 'Unknown':
            if '://' in source:
                domain = source.split('://')[1].split('/')[0]
            else:
                domain = source.split('/')[0]
        elif url:
            if '://' in url:
                domain = url.split('://')[1].split('/')[0]
        
        source_domains[domain] = source_domains.get(domain, 0) + 1
    
    return dict(sorted(source_domains.items(), key=lambda x: x[1], reverse=True))

def check_for_exact_url(url_fragment):
    """Check if any post contains exact URL fragment"""
    try:
        response = table.scan()
        all_posts = response.get('Items', [])
        
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            all_posts.extend(response.get('Items', []))
        
        matches = []
        for post in all_posts:
            url = post.get('url', '')
            if url_fragment in url:
                matches.append(post)
        
        return matches
    except ClientError as e:
        print(f"Error checking for exact URL: {e}")
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
    
    print(f"Total posts loaded for analysis: {len(all_posts)}")
    
    # Count by source
    aws_blog_count = sum(1 for p in all_posts if 'aws.amazon.com' in p.get('source', ''))
    builder_count = sum(1 for p in all_posts if 'builder.aws.com' in p.get('source', ''))
    
    print(f"\nPosts by source:")
    print(f"  AWS Blog: {aws_blog_count}")
    print(f"  Builder.AWS: {builder_count}")
    
    # Debug: Check for the specific missing post
    print("\n" + "="*80)
    print("DEBUGGING: Checking for missing post")
    print("Target: 'Amazon WorkSpaces launches Graphics G6, Gr6, and G6f bundles'")
    print("Expected Date: March 2, 2026 (2026-03-02)")
    print("Expected Source: staging.awseuccontent.com")
    print("="*80)
    
    # Search by title variations
    search_variations = [
        "WorkSpaces launches Graphics",
        "WorkSpaces Graphics G6",
        "Graphics G6",
        "Gr6",
        "G6f bundles",
        "WorkSpaces",
        "Amazon WorkSpaces",
        "Graphics bundles"
    ]
    
    print(f"\n[TEST 1] Searching by title variations...")
    all_matches = []
    for search_title in search_variations:
        matching_posts = check_specific_post(search_title)
        if matching_posts:
            all_matches.extend(matching_posts)
            print(f"  ✓ Found {len(matching_posts)} match(es) for '{search_title}'")
    
    # Deduplicate matches
    unique_matches = {post.get('post_id'): post for post in all_matches}.values()
    
    if unique_matches:
        print(f"\n✓ Total unique matching post(s): {len(unique_matches)}")
        for post in unique_matches:
            print(f"  - {post.get('title')}")
            print(f"    ID: {post.get('post_id')}")
            print(f"    Source: {post.get('source')}")
            print(f"    Date: {post.get('date_published')}")
            print(f"    URL: {post.get('url', 'N/A')}")
            print(f"    Crawled at: {post.get('crawled_timestamp', 'N/A')}")
    else:
        print("  ❌ ISSUE DETECTED: No posts found matching any title variation")
    
    # Comprehensive keyword search across all fields
    print(f"\n[TEST 2] Comprehensive search for 'Graphics G6' across all fields...")
    comprehensive_matches = check_url_in_all_fields('Graphics G6')
    if comprehensive_matches:
        print(f"  ✓ Found {len(comprehensive_matches)} match(es) with 'Graphics G6' anywhere in data:")
        for post in comprehensive_matches[:5]:
            print(f"    - [{post.get('date_published')}] {post.get('title', 'No title')[:60]}...")
    else:
        print("  ❌ ISSUE DETECTED: No posts found with 'Graphics G6' in any field")
    
    # Search by URL pattern for WorkSpaces
    print(f"\n[TEST 3] Searching by URL pattern (workspaces)...")
    workspaces_posts = check_posts_by_url_pattern('workspaces')
    if workspaces_posts:
        print(f"  ✓ Found {len(workspaces_posts)} post(s) with 'workspaces' in URL:")
        for post in workspaces_posts[:5]:
            print(f"    - [{post.get('date_published')}] {post.get('title', 'No title')[:60]}...")
    else:
        print("  ⚠️  No posts found with 'workspaces' in URL")
    
    # Check for posts on March 2, 2026
    target_date = '2026-03-02'
    print(f"\n[TEST 4] Checking for posts published on {target_date}...")
    posts_on_date = check_posts_by_date(target_date)
    
    if posts_on_date:
        print(f"  ✓ Found {len(posts_on_date)} post(s) on {target_date}:")
        for post in posts_on_date:
            print(f"    - {post.get('title', 'No title')}")
            print(f"      Source: {post.get('source', 'Unknown')}")
            print(f"      URL: {post.get('url', 'N/A')}")
    else:
        print(f"  ❌ ISSUE DETECTED: No posts found on {target_date}")
    
    # Check for posts in March 2026
    print(f"\n[TEST 5] Checking for posts in March 2026 (2026-03-01 to 2026-03-31)...")
    march_2026_posts = check_posts_by_date_range('2026-03-01', '2026-03-31')
    
    if march_2026_posts:
        print(f"  ✓ Found {len(march_2026_posts)} post(s) in March 2026:")
        for post in sorted(march_2026_posts, key=lambda x: x.get('date_published', '')):
            print(f"    - [{post.get('date_published')}] {post.get('title', 'No title')[:60]}...")
    else:
        print(f"  ❌ ISSUE DETECTED: No posts found in March 2026")
    
    # Check for posts in 2026
    print(f"\n[TEST 6] Checking for ANY posts in 2026...")
    posts_2026 = [p for p in all_posts if p.get('date_published', '').startswith('2026')]
    
    if posts_2026:
        print(f"  ✓ Found {len(posts_2026)} post(s) in 2026:")
        date_dist_2026 = {}
        for post in posts_2026:
            date = post.get('date_published', 'Unknown')
            date_dist_2026[date] = date_dist_2026.get(date, 0) + 1
        
        for date in sorted(date_dist_2026.keys()):
            print(f"    - {date}: {date_dist_2026[date]} post(s)")
    else:
        print(f"  ❌ CRITICAL ISSUE: No posts found in 2026 at all!")
        print(f"     This strongly suggests date filtering is blocking 2026 dates")
    
    # Check recent posts (last 7 days from now)
    print(f"\n[TEST 7] Checking for posts in the last 7 days from today ({datetime.now().strftime('%Y-%m-%d')})...")
    recent_posts = check_recent_posts(days=7)
    
    if recent_posts:
        print(f"  ✓ Found {len(recent_posts)} recent post(s):")
        for post in sorted(recent_posts, key=lambda x: x.get('date_published', ''), reverse=True)[:10]:
            print(f"    - [{post.get('date_published')}] {post.get('title', 'No title')[:60]}...")
    else:
        print("  ⚠️  No recent posts found in the last 7 days")
    
    # Check for future dates (crawler date filtering issue)
    current_date = datetime.now().strftime('%Y-%m-%d')
    print(f"\n[TEST 8] Checking for posts with future dates (beyond {current_date})...")
    future_posts = [p for p in all_posts if p.get('date_published', '') > current_date]
    
    if future_posts:
        print(f"  ⚠️  Found {len(future_posts)} post(s) with future dates:")
        for post in sorted(future_posts, key=lambda x: x.get('date_published', ''), reverse=True)[:10]:
            print(f"    - [{post.get('date_published')}] {post.get('title', '