```python
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

# Check for the specific Amazon WorkSpaces blog post from March 2, 2026
print("Checking for Amazon WorkSpaces Graphics blog post...\n")
target_url = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'
target_date = '2026-03-02'

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
        print(f"  Expected date: March 2, 2026 ({target_date})")
        print()
        print("  INVESTIGATION STEPS:")
        print("  1. Check if the post exists on the source website")
        print("  2. Verify the crawler is running and targeting desktop-and-application-streaming blog")
        print("  3. Check CloudWatch logs for crawler errors around this date")
        print("  4. Verify the URL pattern matches crawler detection logic")
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
    
    # ENHANCED DETECTION: Check for posts around the target date
    print("\nAnalyzing posts around target date (March 2, 2026)...")
    print("=" * 80)
    
    target_datetime = datetime.strptime(target_date, '%Y-%m-%d')
    date_range_start = (target_datetime - timedelta(days=7)).strftime('%Y-%m-%d')
    date_range_end = (target_datetime + timedelta(days=7)).strftime('%Y-%m-%d')
    
    posts_in_range = [p for p in das_posts if date_range_start <= p.get('date', '') <= date_range_end]
    
    print(f"Posts found between {date_range_start} and {date_range_end}: {len(posts_in_range)}")
    
    if len(posts_in_range) == 0:
        print("✗ WARNING: No posts found in the 2-week window around target date!")
        print("  This suggests the crawler may not be running or detecting new posts.")
    else:
        print(f"✓ Found {len(posts_in_range)} posts in date range")
        for post in posts_in_range:
            print(f"  - {post.get('date')}: {post.get('title', 'No title')[:50]}...")
    
    print()
    
    # Check for gaps in crawling dates
    print("Analyzing crawling frequency...")
    print("=" * 80)
    
    if das_posts:
        most_recent_date = das_posts[0].get('date', '')
        last_crawled = das_posts[0].get('last_crawled', 'Never')
        
        print(f"Most recent post date: {most_recent_date}")
        print(f"Most recent crawl timestamp: {last_crawled}")
        
        if most_recent_date < target_date:
            print(f"✗ WARNING: Most recent post ({most_recent_date}) is older than target ({target_date})")
            print("  The crawler may not be detecting new posts published after this date.")
            print("  Recommended actions:")
            print("  - Check if crawler is scheduled to run regularly")
            print("  - Verify RSS feed or sitemap includes recent posts")
            print("  - Check for changes in blog HTML structure that may break parsing")
        else:
            print(f"✓ Crawler appears to be detecting posts up to {most_recent_date}")
    
    print()
    
except Exception as e:
    print(f"Error scanning desktop-and-application-streaming posts: {str(e)}\n")

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

# ENHANCED: Final diagnosis summary
print("\n" + "=" * 80)
print("DIAGNOSIS SUMMARY")
print("=" * 80)
print("\nIf the target post is still not found, likely causes are:")
print("1. Post was published after the last crawler run")
print("2. Post URL structure doesn't match crawler patterns")
print("3. RSS feed or sitemap doesn't include the post yet")
print("4. Crawler encountered an error parsing the specific post")
print("5. Post is behind authentication or not publicly accessible")
print("\nRecommended next steps:")
print("- Manually trigger a crawler run for desktop-and-application-streaming blog")
print("- Check CloudWatch logs for errors around March 2, 2026")
print("- Verify the post URL is accessible and has expected HTML structure")
print("- Review crawler configuration for date filtering or URL exclusions")
print("=" * 80)
```