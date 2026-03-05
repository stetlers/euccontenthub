```python
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
staging_table = dynamodb.Table('aws-blog-posts-staging')
production_table = dynamodb.Table('aws-blog-posts')

# Check for the specific Amazon WorkSpaces blog post from March 2, 2026
print("=" * 100)
print("INVESTIGATING MISSING BLOG POST: Amazon WorkSpaces Graphics G6 bundles")
print("=" * 100)
print()

target_url = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'
target_date = '2026-03-02'

# Step 1: Check if post exists in staging
print("STEP 1: Checking staging database")
print("-" * 80)
try:
    response = staging_table.get_item(Key={'url': target_url})
    
    if 'Item' in response:
        post = response['Item']
        print("✓ POST FOUND in staging database!")
        print(f"  Title: {post.get('title', 'N/A')}")
        print(f"  Source: {post.get('source', 'N/A')}")
        print(f"  Date: {post.get('date', 'N/A')}")
        print(f"  Last crawled: {post.get('last_crawled', 'Never')}")
        staging_has_post = True
    else:
        print("✗ POST NOT FOUND in staging database!")
        print(f"  Target URL: {target_url}")
        print(f"  Expected date: {target_date} (March 2, 2026)")
        staging_has_post = False
except Exception as e:
    print(f"✗ Error checking staging: {str(e)}")
    staging_has_post = False

print()

# Step 2: Check if post exists in production
print("STEP 2: Checking production database for comparison")
print("-" * 80)
try:
    response = production_table.get_item(Key={'url': target_url})
    
    if 'Item' in response:
        post = response['Item']
        print("✓ POST FOUND in production database!")
        print(f"  Title: {post.get('title', 'N/A')}")
        print(f"  Source: {post.get('source', 'N/A')}")
        print(f"  Date: {post.get('date', 'N/A')}")
        print(f"  Last crawled: {post.get('last_crawled', 'Never')}")
        production_has_post = True
    else:
        print("✗ POST NOT FOUND in production database either")
        print("  This indicates the post may not exist on the blog yet")
        production_has_post = False
except Exception as e:
    print(f"✗ Error checking production: {str(e)}")
    production_has_post = False

print()

# Step 3: Analyze date filtering behavior
print("STEP 3: Analyzing date filtering for Desktop and Application Streaming blog")
print("-" * 80)
try:
    response = staging_table.scan(
        FilterExpression='contains(#url, :blog_path)',
        ExpressionAttributeNames={'#url': 'url'},
        ExpressionAttributeValues={':blog_path': 'aws.amazon.com/blogs/desktop-and-application-streaming/'}
    )
    
    das_posts = response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = staging_table.scan(
            FilterExpression='contains(#url, :blog_path)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':blog_path': 'aws.amazon.com/blogs/desktop-and-application-streaming/'},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        das_posts.extend(response['Items'])
    
    print(f"Total Desktop and Application Streaming posts in staging: {len(das_posts)}")
    
    # Analyze date patterns
    dates_with_posts = {}
    future_posts = []
    recent_posts = []
    
    for post in das_posts:
        post_date = post.get('date', '')
        if post_date:
            dates_with_posts[post_date] = dates_with_posts.get(post_date, 0) + 1
            
            # Check if post is from 2026 or later
            if post_date >= '2026-01-01':
                future_posts.append(post)
            
            # Check if post is from last 30 days
            try:
                post_datetime = datetime.strptime(post_date, '%Y-%m-%d')
                if post_datetime >= datetime.now() - timedelta(days=30):
                    recent_posts.append(post)
            except:
                pass
    
    print(f"Posts from 2026 or later: {len(future_posts)}")
    print(f"Posts from last 30 days: {len(recent_posts)}")
    
    # Check if target date exists
    if target_date in dates_with_posts:
        print(f"✓ Posts found with target date {target_date}: {dates_with_posts[target_date]}")
    else:
        print(f"✗ No posts found with target date {target_date}")
    
    print()
    print("Date range analysis:")
    sorted_dates = sorted(dates_with_posts.keys(), reverse=True)
    if sorted_dates:
        print(f"  Most recent post date: {sorted_dates[0]}")
        print(f"  Oldest post date: {sorted_dates[-1]}")
        print(f"  Target date ({target_date}) is {'within' if target_date <= sorted_dates[0] and target_date >= sorted_dates[-1] else 'outside'} range")
    
    print()
    
    # Show most recent posts including date analysis
    das_posts.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    print("Most recent Desktop and Application Streaming posts (up to 10):")
    print("=" * 100)
    for i, post in enumerate(das_posts[:10], 1):
        print(f"{i}. {post.get('title', 'No title')[:70]}...")
        print(f"   URL: {post.get('url', 'N/A')}")
        print(f"   Date: {post.get('date', 'N/A')}")
        print(f"   Last crawled: {post.get('last_crawled', 'Never')}")
        print()
    
    # Check for posts around target date
    print("Posts within 7 days of target date (2026-03-02):")
    print("=" * 100)
    target_start = '2026-02-23'
    target_end = '2026-03-09'
    nearby_posts = [p for p in das_posts if target_start <= p.get('date', '') <= target_end]
    
    if nearby_posts:
        for i, post in enumerate(nearby_posts, 1):
            print(f"{i}. {post.get('title', 'No title')}")
            print(f"   Date: {post.get('date', 'N/A')}")
            print(f"   URL: {post.get('url', 'N/A')}")
            print()
    else:
        print("✗ No posts found within 7 days of target date")
        print("  This suggests a date filtering issue or crawler timing problem")
    
    print()
    
except Exception as e:
    print(f"Error scanning desktop-and-application-streaming posts: {str(e)}\n")

# Step 4: Check crawler configuration and timing
print("STEP 4: Analyzing crawler behavior and timing")
print("-" * 80)
try:
    # Get all posts with last_crawled timestamps
    response = staging_table.scan()
    all_posts = response['Items']
    
    while 'LastEvaluatedKey' in response:
        response = staging_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        all_posts.extend(response['Items'])
    
    # Analyze last_crawled timestamps
    crawled_times = []
    for post in all_posts:
        if post.get('last_crawled') and post.get('last_crawled') != 'Never':
            crawled_times.append(post.get('last_crawled'))
    
    if crawled_times:
        crawled_times.sort(reverse=True)
        print(f"Total posts with crawl timestamps: {len(crawled_times)}")
        print(f"Most recent crawl: {crawled_times[0]}")
        print(f"Oldest recent crawl: {crawled_times[-1] if len(crawled_times) > 0 else 'N/A'}")
        
        # Check if crawler has run recently
        try:
            most_recent = datetime.fromisoformat(crawled_times[0].replace('Z', '+00:00'))
            hours_since_crawl = (datetime.now(most_recent.tzinfo) - most_recent).total_seconds() / 3600
            print(f"Hours since last crawl: {hours_since_crawl:.1f}")
            
            if hours_since_crawl > 24:
                print("⚠ WARNING: Crawler may not have run in over 24 hours")
        except:
            pass
    else:
        print("✗ No posts have last_crawled timestamps")
        print("  This indicates the crawler may not be running")
    
    print()
    
except Exception as e:
    print(f"Error analyzing crawler timing: {str(e)}\n")

# Step 5: Check Builder.AWS posts (existing functionality)
print("\nSTEP 5: Checking Builder.AWS posts in staging")
print("-" * 80)
try:
    response = staging_table.scan(
        FilterExpression='#src = :builder',
        ExpressionAttributeNames={'#src': 'source'},
        ExpressionAttributeValues={':builder': 'builder.aws.com'}
    )

    builder_posts = response['Items']

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = staging_table.scan(
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
    print("=" * 100)
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
print()
print("=" * 100)
print("INVESTIGATION SUMMARY AND RECOMMENDATIONS")
print("=" * 100)
print()

if not staging_has_post and production_has_post:
    print("FINDING: Post exists in production but not in staging")
    print("LIKELY CAUSE: Staging crawler configuration differs from production")
    print("RECOMMENDATION: Compare staging and production crawler configurations")
elif not staging_has_post and not production_has_post:
    print("FINDING: Post not found in either staging or production")
    print("LIKELY CAUSE: One of the following:")
    print("  1. Post date is in the future and crawler filters future dates")
    print("  2. Post URL or blog path has changed")
    print("  3. Post has not been published yet")
    print("  4. Crawler is not detecting the blog category properly")
    print("RECOMMENDATION:")
    print("  1. Verify the post exists on the AWS blog website")
    print("  2. Check crawler date filtering logic for future dates")
    print("  3. Review URL pattern detection in crawler code")
    print("  4. Check if blog RSS feed includes this category")
else:
    print("FINDING: Post exists in staging - no issue detected")
    print("RECOMMENDATION: Continue monitoring")

print()
```