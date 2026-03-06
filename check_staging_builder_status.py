```python
import boto3
from decimal import Decimal
from datetime import datetime, timedelta
import json

# Connect to staging DynamoDB table
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

# CloudWatch Logs client for checking crawler logs
logs_client = boto3.client('logs', region_name='us-east-1')

# Define the specific blog post we're looking for
TARGET_URL = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'
TARGET_DATE = '2026-03-02'
TARGET_TITLE = 'Amazon WorkSpaces launches Graphics G6, Gr6, and G6f bundles'

print(f"\n{'='*80}")
print(f"Investigating Missing Amazon WorkSpaces Blog Post")
print(f"{'='*80}")
print(f"Target URL: {TARGET_URL}")
print(f"Expected Date: {TARGET_DATE}")
print(f"Expected Title: {TARGET_TITLE}")
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
            print(f"  Created At: {post.get('created_at', 'No timestamp')}")
            print(f"  Updated At: {post.get('updated_at', 'No timestamp')}")
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
            print(f"✓ Found {len(das_posts)} posts from this blog category:")
            # Sort by date and show most recent
            sorted_das_posts = sorted(das_posts, key=lambda x: x.get('publish_date', ''), reverse=True)
            for post in sorted_das_posts[:10]:
                print(f"  - {post.get('publish_date', 'No date')}: {post.get('title', 'No title')[:80]}")
            
            # Check if any posts are from March 2026
            march_2026_posts = [p for p in sorted_das_posts if p.get('publish_date', '').startswith('2026-03')]
            if march_2026_posts:
                print(f"\n  ✓ Found {len(march_2026_posts)} posts from March 2026 in this category")
            else:
                print(f"\n  ✗ No posts from March 2026 found in this category")
                print(f"    Most recent post date: {sorted_das_posts[0].get('publish_date', 'unknown') if sorted_das_posts else 'N/A'}")
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
                print(f"    Category: {post.get('url', '').split('/blogs/')[1].split('/')[0] if '/blogs/' in post.get('url', '') else 'N/A'}")
        else:
            print(f"✗ NO posts found from March 1-3, 2026")
            print(f"  This may indicate the crawler is not processing recent content")
            print(f"  OR date filtering is excluding posts after a certain date")
        
        # Check for posts with future dates (relative to when crawler might consider "today")
        print(f"\nChecking for posts with dates in 2026...")
        response_2026 = table.scan(
            FilterExpression='begins_with(#date, :year)',
            ExpressionAttributeNames={'#date': 'publish_date'},
            ExpressionAttributeValues={':year': '2026'}
        )
        
        posts_2026 = response_2026['Items']
        if posts_2026:
            print(f"Found {len(posts_2026)} posts with 2026 dates:")
            for post in sorted(posts_2026, key=lambda x: x.get('publish_date', ''), reverse=True)[:15]:
                print(f"  - {post.get('publish_date', 'No date')}: {post.get('title', 'No title')[:70]}")
                blog_cat = post.get('url', '').split('/blogs/')[1].split('/')[0] if '/blogs/' in post.get('url', '') else 'N/A'
                print(f"    Category: {blog_cat}")
        else:
            print(f"✗ NO posts found with 2026 dates")
            print(f"  ⚠ CRITICAL: Crawler may be filtering out future dates!")
            print(f"  The target post date ({TARGET_DATE}) may be considered 'future' by crawler")
        
        # Check for posts with missing or malformed dates
        print(f"\nChecking for posts with missing or malformed dates...")
        response_all = table.scan()
        
        posts_with_date_issues = []
        for post in response_all['Items']:
            pub_date = post.get('publish_date', '')
            if not pub_date:
                posts_with_date_issues.append(('missing', post))
            elif not (len(pub_date) == 10 and pub_date.count('-') == 2):
                posts_with_date_issues.append(('malformed', post))
        
        if posts_with_date_issues:
            print(f"⚠ WARNING: Found {len(posts_with_date_issues)} posts with date issues:")
            for issue_type, post in posts_with_date_issues[:10]:
                print(f"  - [{issue_type.upper()}] {post.get('title', 'No title')[:60]}")
                print(f"    Date value: '{post.get('publish_date', 'MISSING')}'")
                print(f"    URL: {post.get('url', 'No URL')[:80]}")
        
        # Check crawler metadata and timestamps
        print(f"\nAnalyzing crawler execution patterns...")
        response_with_timestamps = table.scan()
        
        posts_with_timestamps = [p for p in response_with_timestamps['Items'] if p.get('created_at')]
        
        if posts_with_timestamps:
            # Sort by creation timestamp to find most recent crawl
            posts_by_timestamp = sorted(posts_with_timestamps, 
                                       key=lambda x: x.get('created_at', ''), 
                                       reverse=True)
            
            latest_crawled = posts_by_timestamp[0]
            print(f"Most recently crawled post:")
            print(f"  Title: {latest_crawled.get('title', 'No title')[:80]}")
            print(f"  Created At: {latest_crawled.get('created_at', 'No timestamp')}")
            print(f"  Publish Date: {latest_crawled.get('publish_date', 'No date')}")
            print(f"  Source: {latest_crawled.get('source', 'No source')}")
            
            # Check if crawler has run since target date
            target_datetime = datetime.strptime(TARGET_DATE, '%Y-%m-%d')
            latest_crawl_time = latest_crawled.get('created_at', '')
            
            if latest_crawl_time:
                try:
                    # Handle various timestamp formats
                    if 'Z' in latest_crawl_time:
                        latest_datetime = datetime.fromisoformat(latest_crawl_time.replace('Z', '+00:00'))
                    elif '+' in latest_crawl_time or latest_crawl_time.endswith('00:00'):
                        latest_datetime = datetime.fromisoformat(latest_crawl_time)
                    else:
                        latest_datetime = datetime.strptime(latest_crawl_time[:19], '%Y-%m-%d %H:%M:%S')
                    
                    print(f"\n  Last crawl execution: {latest_datetime}")
                    print(f"  Target post date: {target_datetime}")
                    
                    if latest_datetime.date() < target_datetime.date():
                        print(f"\n  ⚠ WARNING: Last crawl was BEFORE target post date!")
                        print(f"    Days difference: {(target_datetime.date() - latest_datetime.date()).days}")
                        print(f"    Action: Crawler needs to run to pick up posts from {TARGET_DATE}")
                    else:
                        print(f"\n  ✓ Crawler has run after target post date")
                        print(f"    The post should have been detected if URL is correct")
                except Exception as e:
                    print(f"  Could not parse crawl timestamp: {e}")
        else:
            print(f"✗ No posts with creation timestamps found")
        
        # Check for URL variations or partial matches
        print(f"\nChecking for URL variations or partial matches...")
        url_parts = [
            'amazon-workspaces-launches-graphics',
            'g6-gr6-and-g6f-bundles',
            'workspaces-launches-graphics',
            'graphics-g6-gr6-and-g6f',
            'amazon-workspaces-launches',
            'workspaces-graphics'
        ]
        
        found_any_variation = False
        for url_part in url_parts:
            response_variation = table.scan(
                FilterExpression='contains(#url, :url_part)',
                ExpressionAttributeNames={'#url': 'url'},
                ExpressionAttributeValues={':url_part': url_part}
            )
            
            if response_variation['Items']:
                found_any_variation = True
                print(f"  ✓ Found {len(response_variation['Items'])} posts containing '{url_part}':")
                for post in response_variation['Items'][:3]:
                    print(f"    - {post.get('url', 'No URL')}")
                    print(f"      Date: {post.get('publish_date', 'No date')}, Title: {post.get('title', 'No title')[:50]}")
        
        if not found_any_variation:
            print(f"  ✗ No URL variations found - post likely not crawled yet")

except Exception as e:
    print(f"Error during specific post search: {str(e)}")
    import traceback
    traceback.print_exc()

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

# Enhanced diagnostics for crawler configuration
print(f"\n{'='*80}")
print(f"CRAWLER DIAGNOSTICS")
print(f"{'='*80}")

try:
    # Check all unique sources to verify crawler coverage
    response_all_posts = table.scan()
    all_posts = response_all_posts['Items']
    
    sources = set()
    blog_categories = set()
    
    for post in all_posts:
        source = post.get('source', 'unknown')
        sources.add(source)
        
        url = post.get('url', '')
        if '/blogs/' in url:
            # Extract blog category from URL
            parts = url.split('/blogs/')
            if len(parts) > 1:
                category = parts[1].split('/')[0]
                blog_categories.add(category)
    
    print(f"\nTotal posts in staging: {len(all_posts)}")
    print(f"Total unique sources: {len(sources)}")
    print(f"Sources found: {', '.join(sorted(sources))}")
    print(f"\nTotal unique blog categories: {len(blog_categories)}")
    print(f"Blog categories (showing all):")