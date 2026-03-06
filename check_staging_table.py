```python
#!/usr/bin/env python3
"""Check what's in the staging table and debug crawler issues"""

import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
import json
import sys
import requests
from urllib.parse import urlparse

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

def check_posts_by_source(source_pattern):
    """Search for posts by source pattern"""
    try:
        response = table.scan(
            FilterExpression='contains(#source, :pattern)',
            ExpressionAttributeNames={'#source': 'source'},
            ExpressionAttributeValues={':pattern': source_pattern}
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error searching by source pattern: {e}")
        return []

def verify_url_accessibility(url):
    """Verify if a URL is accessible via HTTP request"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; AWS Blog Crawler Debug/1.0)'
        }
        response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        return {
            'accessible': response.status_code == 200,
            'status_code': response.status_code,
            'final_url': response.url,
            'headers': dict(response.headers)
        }
    except requests.RequestException as e:
        return {
            'accessible': False,
            'error': str(e)
        }

def check_staging_domain_posts():
    """Check for posts from staging.awseuccontent.com domain"""
    try:
        response = table.scan(
            FilterExpression='contains(#source, :domain) OR contains(#url, :domain)',
            ExpressionAttributeNames={
                '#source': 'source',
                '#url': 'url'
            },
            ExpressionAttributeValues={':domain': 'staging.awseuccontent.com'}
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error checking staging domain posts: {e}")
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

def analyze_date_filtering_logic(all_posts):
    """Analyze potential date filtering issues in crawler"""
    current_date = datetime.now()
    
    # Group posts by relationship to current date
    past_posts = []
    future_posts = []
    invalid_dates = []
    
    for post in all_posts:
        date_str = post.get('date_published', '')
        if not date_str or date_str == 'Unknown':
            invalid_dates.append(post)
            continue
        
        try:
            post_date = datetime.strptime(date_str, '%Y-%m-%d')
            if post_date > current_date:
                future_posts.append((post_date, post))
            else:
                past_posts.append((post_date, post))
        except ValueError:
            invalid_dates.append(post)
    
    return {
        'past_posts_count': len(past_posts),
        'future_posts_count': len(future_posts),
        'invalid_dates_count': len(invalid_dates),
        'latest_past_date': max([d for d, _ in past_posts]) if past_posts else None,
        'earliest_future_date': min([d for d, _ in future_posts]) if future_posts else None,
        'future_posts': sorted(future_posts, key=lambda x: x[0])
    }

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
    
    # Analyze all attributes in the table
    print(f"\n[SCHEMA ANALYSIS] Analyzing table structure...")
    all_attributes, attribute_examples = check_all_attributes(all_posts)
    print(f"  Attributes found in posts: {', '.join(all_attributes)}")
    print(f"\n  Sample values:")
    for attr, example in attribute_examples.items():
        print(f"    - {attr}: {example}")
    
    # Count by source
    aws_blog_count = sum(1 for p in all_posts if 'aws.amazon.com' in p.get('source', ''))
    builder_count = sum(1 for p in all_posts if 'builder.aws.com' in p.get('source', ''))
    staging_count = sum(1 for p in all_posts if 'staging.awseuccontent.com' in p.get('source', '') or 'staging.awseuccontent.com' in p.get('url', ''))
    
    print(f"\nPosts by source:")
    print(f"  AWS Blog: {aws_blog_count}")
    print(f"  Builder.AWS: {builder_count}")
    print(f"  Staging.awseuccontent.com: {staging_count}")
    
    # Analyze all source domains
    print(f"\n[SOURCE ANALYSIS] All source domains found:")
    source_domains = analyze_source_patterns(all_posts)
    for domain, count in list(source_domains.items())[:10]:
        print(f"  - {domain}: {count} post(s)")
    
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
    target_date = '2026