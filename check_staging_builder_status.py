```python
import boto3
from decimal import Decimal
from datetime import datetime, timedelta

# Connect to both staging and production DynamoDB tables for comparison
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
staging_table = dynamodb.Table('aws-blog-posts-staging')
production_table = dynamodb.Table('aws-blog-posts-production')

# Define the specific blog post we're looking for
TARGET_URL = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'
TARGET_DATE = '2026-03-02'
TARGET_BLOG_CATEGORY = 'desktop-and-application-streaming'
TARGET_URL_SLUG = 'amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles'

print(f"\n{'='*80}")
print(f"Investigating Missing Amazon WorkSpaces Blog Post")
print(f"{'='*80}")
print(f"Target URL: {TARGET_URL}")
print(f"Expected Date: {TARGET_DATE}")
print(f"Blog Category: {TARGET_BLOG_CATEGORY}")
print(f"{'='*80}\n")

def check_table_for_post(table, table_name):
    """Check if the target post exists in a specific DynamoDB table"""
    print(f"\n{'='*80}")
    print(f"Checking {table_name} Table")
    print(f"{'='*80}")
    
    try:
        # Check for the specific blog post
        response = table.scan(
            FilterExpression='contains(#url, :url_part)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':url_part': TARGET_URL_SLUG}
        )
        
        if response['Items']:
            print(f"✓ FOUND the target blog post in {table_name}!")
            for post in response['Items']:
                print(f"\n  Post ID: {post['post_id']}")
                print(f"  Title: {post.get('title', 'No title')}")
                print(f"  URL: {post.get('url', 'No URL')}")
                print(f"  Date: {post.get('publish_date', 'No date')}")
                print(f"  Source: {post.get('source', 'No source')}")
                print(f"  Crawled At: {post.get('crawled_at', 'No timestamp')}")
            return True
        else:
            print(f"✗ Target blog post NOT FOUND in {table_name}")
            return False
            
    except Exception as e:
        print(f"Error during specific post search in {table_name}: {str(e)}")
        return False

def analyze_blog_category_coverage(table, table_name):
    """Analyze coverage of the desktop-and-application-streaming blog category"""
    print(f"\n{'='*80}")
    print(f"Analyzing Blog Category Coverage in {table_name}")
    print(f"{'='*80}")
    
    try:
        response = table.scan(
            FilterExpression='contains(#url, :blog_category)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':blog_category': TARGET_BLOG_CATEGORY}
        )
        
        das_posts = response['Items']
        if das_posts:
            print(f"Found {len(das_posts)} posts from {TARGET_BLOG_CATEGORY} blog:")
            sorted_posts = sorted(das_posts, key=lambda x: x.get('publish_date', ''), reverse=True)
            
            # Show most recent posts
            print(f"\nMost recent 10 posts:")
            for post in sorted_posts[:10]:
                print(f"  - {post.get('publish_date', 'No date')}: {post.get('title', 'No title')[:80]}")
            
            # Analyze date range
            dates = [p.get('publish_date') for p in das_posts if p.get('publish_date')]
            if dates:
                print(f"\nDate range: {min(dates)} to {max(dates)}")
                
                # Check if any posts are from March 2026
                march_2026_posts = [p for p in das_posts if p.get('publish_date', '').startswith('2026-03')]
                print(f"Posts from March 2026: {len(march_2026_posts)}")
                
                if march_2026_posts:
                    for post in march_2026_posts:
                        print(f"  - {post.get('publish_date')}: {post.get('title', 'No title')[:80]}")
            
            return das_posts
        else:
            print(f"✗ NO posts found from {TARGET_BLOG_CATEGORY} blog")
            print(f"  This indicates the crawler may not be configured for this blog category")
            return []
            
    except Exception as e:
        print(f"Error during blog category analysis in {table_name}: {str(e)}")
        return []

def check_date_range_coverage(table, table_name):
    """Check for posts published around the target date"""
    print(f"\n{'='*80}")
    print(f"Checking Date Range Coverage in {table_name}")
    print(f"{'='*80}")
    
    try:
        # Check for posts around the target date
        response = table.scan(
            FilterExpression='#date >= :start_date AND #date <= :end_date',
            ExpressionAttributeNames={'#date': 'publish_date'},
            ExpressionAttributeValues={
                ':start_date': '2026-03-01',
                ':end_date': '2026-03-05'
            }
        )
        
        recent_posts = response['Items']
        if recent_posts:
            print(f"Found {len(recent_posts)} posts from March 1-5, 2026:")
            for post in sorted(recent_posts, key=lambda x: x.get('publish_date', '')):
                print(f"  - {post.get('publish_date', 'No date')}: {post.get('title', 'No title')[:80]}")
                print(f"    Source: {post.get('source', 'No source')}")
                print(f"    URL: {post.get('url', 'No URL')[:100]}")
            return recent_posts
        else:
            print(f"✗ NO posts found from March 1-5, 2026 in {table_name}")
            
            # Check for the most recent posts to identify date filtering issues
            print(f"\nChecking for most recent posts in {table_name}...")
            all_posts_response = table.scan()
            all_posts = all_posts_response['Items']
            
            if all_posts:
                dates_with_posts = [(p.get('publish_date', ''), p.get('title', 'No title')[:80]) 
                                   for p in all_posts if p.get('publish_date')]
                dates_with_posts.sort(reverse=True)
                
                print(f"\nMost recent 10 posts by date:")
                for date, title in dates_with_posts[:10]:
                    print(f"  - {date}: {title}")
                
                if dates_with_posts:
                    most_recent_date = dates_with_posts[0][0]
                    print(f"\nMost recent post date: {most_recent_date}")
                    if most_recent_date < TARGET_DATE:
                        print(f"⚠ WARNING: Most recent post ({most_recent_date}) is older than target date ({TARGET_DATE})")
                        print(f"  This suggests the crawler may have a date filter or cutoff preventing recent posts")
            
            return []
            
    except Exception as e:
        print(f"Error during date range check in {table_name}: {str(e)}")
        return []

def analyze_crawler_configuration(table, table_name):
    """Analyze crawler behavior by examining post patterns"""
    print(f"\n{'='*80}")
    print(f"Analyzing Crawler Configuration for {table_name}")
    print(f"{'='*80}")
    
    try:
        # Get all posts to analyze patterns
        response = table.scan()
        all_posts = response['Items']
        
        if not all_posts:
            print(f"✗ No posts found in {table_name}")
            return
        
        # Analyze by source/blog
        sources = {}
        for post in all_posts:
            url = post.get('url', '')
            if 'aws.amazon.com/blogs/' in url:
                # Extract blog category from URL
                try:
                    blog_part = url.split('aws.amazon.com/blogs/')[1]
                    blog_category = blog_part.split('/')[0]
                    sources[blog_category] = sources.get(blog_category, 0) + 1
                except:
                    pass
        
        print(f"\nBlog categories being crawled (top 20):")
        sorted_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)
        for blog, count in sorted_sources[:20]:
            indicator = "✓" if blog == TARGET_BLOG_CATEGORY else " "
            print(f"  {indicator} {blog}: {count} posts")
        
        if TARGET_BLOG_CATEGORY not in sources:
            print(f"\n✗ ISSUE DETECTED: '{TARGET_BLOG_CATEGORY}' is NOT in the list of crawled blogs")
            print(f"  Action Required: Add this blog category to the crawler configuration")
        elif sources[TARGET_BLOG_CATEGORY] < 5:
            print(f"\n⚠ WARNING: '{TARGET_BLOG_CATEGORY}' has only {sources[TARGET_BLOG_CATEGORY]} posts")
            print(f"  This suggests limited or incomplete crawling of this blog")
        
        # Check for date filtering issues
        dates = [p.get('publish_date') for p in all_posts if p.get('publish_date')]
        if dates:
            min_date = min(dates)
            max_date = max(dates)
            print(f"\nOverall date range in {table_name}: {min_date} to {max_date}")
            
            if max_date < TARGET_DATE:
                print(f"\n✗ ISSUE DETECTED: Latest post date ({max_date}) is before target date ({TARGET_DATE})")
                print(f"  Possible causes:")
                print(f"    1. Crawler has not run recently")
                print(f"    2. Date filter is excluding future dates")
                print(f"    3. Crawler is failing to process recent posts")
        
    except Exception as e:
        print(f"Error during crawler configuration analysis: {str(e)}")

def compare_staging_and_production():
    """Compare staging and production to identify differences"""
    print(f"\n{'='*80}")
    print(f"Comparing Staging vs Production")
    print(f"{'='*80}")
    
    try:
        # Check if post exists in production but not staging
        prod_response = production_table.scan(
            FilterExpression='contains(#url, :url_part)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':url_part': TARGET_URL_SLUG}
        )
        
        staging_response = staging_table.scan(
            FilterExpression='contains(#url, :url_part)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':url_part': TARGET_URL_SLUG}
        )
        
        in_production = len(prod_response['Items']) > 0
        in_staging = len(staging_response['Items']) > 0
        
        print(f"\nTarget post presence:")
        print(f"  Production: {'✓ Found' if in_production else '✗ Not found'}")
        print(f"  Staging: {'✓ Found' if in_staging else '✗ Not found'}")
        
        if in_production and not in_staging:
            print(f"\n✗ CRITICAL ISSUE: Post exists in production but NOT in staging")
            print(f"  This indicates staging crawler is not working properly")
        elif not in_production and not in_staging:
            print(f"\n⚠ Post not found in either environment")
            print(f"  This may indicate the post doesn't exist yet or URL is incorrect")
        
    except Exception as e:
        print(f"Note: Could not compare with production (table may not exist): {str(e)}")

# Execute all checks for staging
found_in_staging = check_table_for_post(staging_table, "STAGING")
analyze_blog_category_coverage(staging_table, "STAGING")
check_date_range_coverage(staging_table, "STAGING")
analyze_crawler_configuration(staging_table, "STAGING")

# Compare with production
compare_staging_and_production()

# Original Builder.AWS posts status check
print(f"\n{'='*80}")
print(f"Builder.AWS Posts Status in Staging")
print(f"{'='*80}")

try:
    response = staging_table.scan(
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

    print(f"Total posts: {total}")
    print(f"Posts with real authors: {with_authors}/{total}")
    print(f"Posts with content (>100 chars): {with_content}/{total}")
    print(f"Posts with summaries: {with_summaries}/{total}")
    print(f"Posts with labels: {with_labels}/{total}")

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

# Enhanced recommendations based on analysis
print(f"\n{'='*80}")
print(f"DIAGNOSTIC SUMMARY & RECOMMENDATIONS")
print(f"{'='*80}")
print(f"\nPrimary Checks:")
print(f"  1. Is '{TARGET_BLOG_CATEGORY}' configured in crawler's blog list?")
print(f"  2. Does the crawler have date filtering that excludes {TARGET_DATE}?")
print(f"  3. Is the crawler running and completing successfully?")
print(f"  4. Are there any errors in crawler logs for this specific blog category?")
print(f"\nVerification Steps:")
print(f"  1. Check crawler configuration for blog category whitelist/blacklist")
print(f"  2. Review crawler logs for errors or warnings about {TARGET_BLOG_CATEGORY}")
print(f"  3. Verify the blog post is publicly accessible at: {TARGET_URL}")
print(f"  4. Check if there are URL encoding, redirect