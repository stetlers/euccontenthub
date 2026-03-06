```python
import boto3
from decimal import Decimal
from datetime import datetime, timedelta

# Connect to staging DynamoDB table
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

# Define the specific blog post we're looking for
TARGET_URL = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'
TARGET_DATE = '2026-03-02'

print(f"\n{'='*80}")
print(f"Investigating Missing Amazon WorkSpaces Blog Post")
print(f"{'='*80}")
print(f"Target URL: {TARGET_URL}")
print(f"Expected Date: {TARGET_DATE}")
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
            print(f"Found {len(das_posts)} posts from this blog category:")
            for post in sorted(das_posts, key=lambda x: x.get('publish_date', ''), reverse=True)[:10]:
                print(f"  - {post.get('publish_date', 'No date')}: {post.get('title', 'No title')[:80]}")
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
        else:
            print(f"✗ NO posts found from March 1-3, 2026")
            print(f"  This may indicate the crawler is not processing recent content")
        
        # NEW: Check for posts with future dates or incorrect date parsing
        print(f"\nChecking for posts with future dates or date parsing issues...")
        today = datetime.now().strftime('%Y-%m-%d')
        future_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
        
        response_future = table.scan(
            FilterExpression='#date > :today',
            ExpressionAttributeNames={'#date': 'publish_date'},
            ExpressionAttributeValues={':today': today}
        )
        
        future_posts = response_future['Items']
        if future_posts:
            print(f"⚠ WARNING: Found {len(future_posts)} posts with future dates:")
            for post in sorted(future_posts, key=lambda x: x.get('publish_date', ''), reverse=True)[:10]:
                print(f"  - {post.get('publish_date', 'No date')}: {post.get('title', 'No title')[:80]}")
                print(f"    URL: {post.get('url', 'No URL')}")
        
        # NEW: Check for posts with missing or malformed dates
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
        
        # NEW: Check crawler metadata and timestamps
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
                    latest_datetime = datetime.fromisoformat(latest_crawl_time.replace('Z', '+00:00'))
                    if latest_datetime.date() < target_datetime.date():
                        print(f"\n⚠ WARNING: Last crawl was before target post date!")
                        print(f"  Crawler may need to run to pick up the new post")
                except Exception as e:
                    print(f"  Could not parse crawl timestamp: {e}")
        
        # NEW: Check for URL variations or redirects
        print(f"\nChecking for URL variations or partial matches...")
        url_parts = [
            'amazon-workspaces-launches-graphics',
            'g6-gr6-and-g6f-bundles',
            'workspaces-launches-graphics',
            'graphics-g6-gr6-and-g6f'
        ]
        
        for url_part in url_parts:
            response_variation = table.scan(
                FilterExpression='contains(#url, :url_part)',
                ExpressionAttributeNames={'#url': 'url'},
                ExpressionAttributeValues={':url_part': url_part}
            )
            
            if response_variation['Items']:
                print(f"  Found {len(response_variation['Items'])} posts containing '{url_part}':")
                for post in response_variation['Items'][:3]:
                    print(f"    - {post.get('url', 'No URL')}")
                    print(f"      Date: {post.get('publish_date', 'No date')}")

except Exception as e:
    print(f"Error during specific post search: {str(e)}")

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

# NEW: Enhanced diagnostics for crawler configuration
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
    
    print(f"Total unique sources: {len(sources)}")
    print(f"Sources found: {', '.join(sorted(sources))}")
    print(f"\nTotal unique blog categories: {len(blog_categories)}")
    print(f"Blog categories (showing first 20):")
    for category in sorted(blog_categories)[:20]:
        print(f"  - {category}")
    
    if 'desktop-and-application-streaming' not in blog_categories:
        print(f"\n⚠ CRITICAL: 'desktop-and-application-streaming' NOT in crawled categories!")
        print(f"  Action required: Add this blog category to crawler configuration")
    else:
        print(f"\n✓ 'desktop-and-application-streaming' IS in crawled categories")
        
    # Check date distribution to identify filtering issues
    print(f"\nDate distribution analysis:")
    date_counts = {}
    for post in all_posts:
        pub_date = post.get('publish_date', 'unknown')
        year_month = pub_date[:7] if len(pub_date) >= 7 else 'unknown'
        date_counts[year_month] = date_counts.get(year_month, 0) + 1
    
    print(f"Posts by year-month (showing recent periods):")
    for year_month in sorted(date_counts.keys(), reverse=True)[:12]:
        print(f"  {year_month}: {date_counts[year_month]} posts")
    
    if '2026-03' not in date_counts or date_counts.get('2026-03', 0) == 0:
        print(f"\n⚠ WARNING: No posts found for March 2026!")
        print(f"  This suggests date filtering or crawler recency issues")

except Exception as e:
    print(f"Error during crawler diagnostics: {str(e)}")

# Summary and recommendations
print(f"\n{'='*80}")
print(f"RECOMMENDATIONS")
print(f"{'='*80}")
print(f"1. Verify the crawler configuration includes 'desktop-and-application-streaming' blog")
print(f"2. Check crawler logs for errors when processing this URL")
print(f"3. Verify the blog post is publicly accessible at the target URL")
print(f"4. Check if there are URL encoding or redirect issues")
print(f"5. Ensure the crawler is running and completing successfully")
print(f"6. Verify the publish date is being parsed correctly from the blog post")
print(f"7. Check if date filtering logic is excluding posts with dates >= {TARGET_DATE}")
print(f"8. Verify crawler's date range configuration (may be filtering future dates)")
print(f"9. Check if blog category is in the crawler's whitelist/configuration")
print(f"10. Review crawler execution schedule and last successful run timestamp")
print(f"11. Inspect RSS feed or sitemap for this blog category to verify post presence")
print(f"12. Check for metadata parsing issues (og:published_time, article:published_time)")
print(f"{'='*80}\n")
```