```python
import boto3
from datetime import datetime, timedelta
import time

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

# Check for the specific Amazon WorkSpaces blog post from March 2, 2026
print("Checking for Amazon WorkSpaces Graphics blog post...\n")
target_url = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'

try:
    # Try to get the specific post by URL
    response = table.get_item(Key={'url': target_url})
    
    if 'Item' in response:
        post = response['Item']
        print("✓ POST FOUND in staging database!")
        print(f"  Title: {post.get('title', 'N/A')}")
        print(f"  Source: {post.get('source', 'N/A')}")
        print(f"  Date: {post.get('date', 'N/A')}")
        print(f"  Last crawled: {post.get('last_crawled', 'Never')}")
        print()
    else:
        print("✗ POST NOT FOUND in staging database!")
        print(f"  Target URL: {target_url}")
        print(f"  Expected date: March 2, 2026")
        print()
except Exception as e:
    print(f"✗ Error checking for specific post: {str(e)}\n")

# Check all desktop-and-application-streaming blog posts
print("Checking all Desktop and Application Streaming blog posts...\n")
try:
    response = table.scan(
        FilterExpression='contains(#url, :blog_path)',
        ExpressionAttributeNames={'#url': 'url'},
        ExpressionAttributeValues={':blog_path': 'aws.amazon.com/blogs/desktop-and-application-streaming/'}
    )
    
    das_posts = response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='contains(#url, :blog_path)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':blog_path': 'aws.amazon.com/blogs/desktop-and-application-streaming/'},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        das_posts.extend(response['Items'])
    
    print(f"Total Desktop and Application Streaming posts: {len(das_posts)}\n")
    
    # Sort by date and show most recent posts
    das_posts.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    print("Most recent posts (up to 10):")
    print("=" * 80)
    for i, post in enumerate(das_posts[:10], 1):
        print(f"{i}. {post.get('title', 'No title')[:70]}...")
        print(f"   URL: {post.get('url', 'N/A')[:70]}...")
        print(f"   Date: {post.get('date', 'N/A')}")
        print(f"   Last crawled: {post.get('last_crawled', 'Never')}")
        print()
    
    # Analyze date range to detect date filtering issues
    print("\nDATE FILTERING ANALYSIS:")
    print("=" * 80)
    if das_posts:
        dates = [p.get('date', '') for p in das_posts if p.get('date')]
        if dates:
            print(f"Date range: {min(dates)} to {max(dates)}")
            
            # Check if recent dates are missing
            target_date = '2026-03-02'
            posts_on_target = [p for p in das_posts if p.get('date', '').startswith(target_date)]
            print(f"Posts on {target_date}: {len(posts_on_target)}")
            
            # Check for posts in the last 30 days from target date
            recent_posts = [p for p in das_posts if p.get('date', '') >= '2026-02-01']
            print(f"Posts since 2026-02-01: {len(recent_posts)}")
            
            # Display date distribution
            date_counts = {}
            for post in das_posts:
                date = post.get('date', '')
                if date:
                    month_key = date[:7]  # YYYY-MM
                    date_counts[month_key] = date_counts.get(month_key, 0) + 1
            
            print("\nPosts by month (most recent 6 months):")
            for month in sorted(date_counts.keys(), reverse=True)[:6]:
                print(f"  {month}: {date_counts[month]} posts")
        else:
            print("No valid dates found in posts")
    else:
        print("No posts found to analyze")
    
    print()
    
except Exception as e:
    print(f"Error scanning desktop-and-application-streaming posts: {str(e)}\n")

# Check for URL pattern variations that might be missed
print("\nURL PATTERN DETECTION ANALYSIS:")
print("=" * 80)
try:
    # Check for posts with various URL patterns
    url_patterns_to_check = [
        'amazon-workspaces',
        'workspaces-graphics',
        'graphics-g6',
        'g6-gr6-g6f',
        'bundles'
    ]
    
    print("Checking for posts containing key terms in URL:")
    for pattern in url_patterns_to_check:
        response = table.scan(
            FilterExpression='contains(#url, :pattern)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':pattern': pattern}
        )
        
        matching_posts = response['Items']
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression='contains(#url, :pattern)',
                ExpressionAttributeNames={'#url': 'url'},
                ExpressionAttributeValues={':pattern': pattern},
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            matching_posts.extend(response['Items'])
        
        print(f"  '{pattern}': {len(matching_posts)} posts")
        
        # Show WorkSpaces-related posts from 2026
        if pattern == 'amazon-workspaces' and matching_posts:
            recent_ws = [p for p in matching_posts if p.get('date', '').startswith('2026')]
            if recent_ws:
                print(f"    Recent WorkSpaces posts in 2026: {len(recent_ws)}")
                for post in sorted(recent_ws, key=lambda x: x.get('date', ''), reverse=True)[:3]:
                    print(f"      - {post.get('date')}: {post.get('title', 'N/A')[:50]}...")
    
    print()
    
except Exception as e:
    print(f"Error in URL pattern analysis: {str(e)}\n")

# Check crawler timestamp and last run information
print("\nCRAWLER EXECUTION ANALYSIS:")
print("=" * 80)
try:
    # Get all posts and check their last_crawled timestamps
    response = table.scan()
    all_posts = response['Items']
    
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        all_posts.extend(response['Items'])
    
    # Analyze crawl timestamps
    crawl_times = [p.get('last_crawled', '') for p in all_posts if p.get('last_crawled')]
    
    if crawl_times:
        crawl_times.sort(reverse=True)
        print(f"Total posts with crawl timestamps: {len(crawl_times)}")
        print(f"Most recent crawl: {crawl_times[0] if crawl_times else 'Never'}")
        print(f"Oldest crawl: {crawl_times[-1] if crawl_times else 'Never'}")
        
        # Check distribution of recent crawls
        now = datetime.utcnow()
        last_24h = (now - timedelta(hours=24)).isoformat()
        last_week = (now - timedelta(days=7)).isoformat()
        
        crawled_24h = [t for t in crawl_times if t >= last_24h]
        crawled_week = [t for t in crawl_times if t >= last_week]
        
        print(f"\nPosts crawled in last 24 hours: {len(crawled_24h)}")
        print(f"Posts crawled in last 7 days: {len(crawled_week)}")
        
        # Check if desktop-and-application-streaming blog was recently crawled
        das_crawled = [p for p in das_posts if p.get('last_crawled', '') >= last_24h]
        print(f"Desktop/App Streaming posts crawled in last 24h: {len(das_crawled)}")
    else:
        print("No crawl timestamps found - crawler may not be running")
    
    print()
    
except Exception as e:
    print(f"Error in crawler execution analysis: {str(e)}\n")

# Get Builder.AWS posts
print("\nChecking Builder.AWS posts in staging...\n")
try:
    response = table.scan(
        FilterExpression='#src = :builder',
        ExpressionAttributeNames={'#src': 'source'},
        ExpressionAttributeValues={':builder': 'builder.aws.com'}
    )

    builder_posts = response['Items']

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='#src = :builder',
            ExpressionAttributeNames={'#src': 'source'},
            ExpressionAttributeValues={':builder': 'builder.aws.com'},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        builder_posts.extend(response['Items'])

    print(f"Total Builder.AWS posts: {len(builder_posts)}\n")

    # Check for issues
    missing_authors = [p for p in builder_posts if p.get('authors') == 'AWS Builder Community']
    missing_summaries = [p for p in builder_posts if not p.get('summary') or p.get('summary') == '']

    print("CRITICAL ISSUES:")
    print("=" * 80)
    print(f"Posts with generic 'AWS Builder Community' author: {len(missing_authors)}")
    print(f"Posts without summaries: {len(missing_summaries)}")

    print("\nSample posts with generic author (first 5):")
    for i, post in enumerate(missing_authors[:5], 1):
        print(f"{i}. {post.get('title', 'No title')[:60]}...")
        print(f"   Author: {post.get('authors')}")
        print(f"   Last crawled: {post.get('last_crawled', 'Never')}")
        print(f"   Has summary: {'Yes' if post.get('summary') else 'No'}")
        print()

except Exception as e:
    print(f"Error scanning Builder.AWS posts: {str(e)}\n")

# Summary and recommendations
print("\nDIAGNOSTIC SUMMARY:")
print("=" * 80)
print("The following areas should be investigated in the crawler code:")
print("1. Date filtering logic - verify posts from March 2026 are not being filtered out")
print("2. URL detection patterns - ensure all AWS blog post URLs are being captured")
print("3. Crawler execution frequency - check if crawler is running on schedule")
print("4. Scraping patterns - verify HTML parsing is working for new blog post formats")
print("5. Error handling - check crawler logs for any failures or exceptions")
print("\nRecommended next steps:")
print("- Review crawler Lambda function logs in CloudWatch")
print("- Verify RSS feed parsing for desktop-and-application-streaming blog")
print("- Test crawler manually against the target URL")
print("- Check for any rate limiting or access issues with aws.amazon.com")
print()
```