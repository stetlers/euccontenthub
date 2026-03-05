```python
import boto3
from datetime import datetime, timedelta
import re

logs_client = boto3.client('logs', region_name='us-east-1')

print("=" * 60)
print("Detailed Sitemap Crawler Logs - Enhanced Debugging")
print("=" * 60)

log_group = '/aws/lambda/aws-blog-crawler'
# Extended time window to capture more historical logs
start_time = int((datetime.now() - timedelta(hours=2)).timestamp() * 1000)

# Target blog post URL to track
target_url = "amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles"
target_date = "2026-03-02"

try:
    response = logs_client.filter_log_events(
        logGroupName=log_group,
        startTime=start_time,
        filterPattern=''
    )
    
    print(f"\nTotal log events: {len(response['events'])}\n")
    
    # Statistics tracking
    sitemap_urls_found = []
    blog_posts_processed = []
    workspaces_posts = []
    target_post_found = False
    error_patterns = []
    
    print("=" * 60)
    print("SEARCHING FOR TARGET POST")
    print("=" * 60)
    print(f"Target URL fragment: {target_url}")
    print(f"Target date: {target_date}\n")
    
    # Analyze all events for patterns
    for event in response['events']:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event['message'].strip()
        
        # Track sitemap processing
        if 'sitemap' in message.lower() and 'processing' in message.lower():
            sitemap_urls_found.append(message)
        
        # Track blog post URLs being processed
        if '/blogs/desktop-and-application-streaming/' in message:
            blog_posts_processed.append(message)
            if 'workspaces' in message.lower():
                workspaces_posts.append(message)
        
        # Check for target post
        if target_url in message or target_date in message:
            target_post_found = True
            print(f"[FOUND] {timestamp.strftime('%Y-%m-%d %H:%M:%S')} | {message}")
        
        # Track errors
        if any(keyword in message.lower() for keyword in ['error', 'failed', 'exception', 'timeout']):
            error_patterns.append((timestamp, message))
    
    # Summary statistics
    print("\n" + "=" * 60)
    print("CRAWLER STATISTICS")
    print("=" * 60)
    print(f"Sitemaps processed: {len(sitemap_urls_found)}")
    print(f"Blog posts found: {len(blog_posts_processed)}")
    print(f"WorkSpaces-related posts: {len(workspaces_posts)}")
    print(f"Target post detected: {'YES' if target_post_found else 'NO'}")
    print(f"Errors encountered: {len(error_patterns)}")
    
    # Display sitemap information
    if sitemap_urls_found:
        print("\n" + "=" * 60)
        print("SITEMAPS PROCESSED")
        print("=" * 60)
        for sitemap in sitemap_urls_found[:10]:
            print(f"  - {sitemap}")
    
    # Display WorkSpaces posts found
    if workspaces_posts:
        print("\n" + "=" * 60)
        print("WORKSPACES BLOG POSTS FOUND")
        print("=" * 60)
        for post in workspaces_posts[:20]:
            print(f"  - {post}")
    
    # Display errors if any
    if error_patterns:
        print("\n" + "=" * 60)
        print("ERRORS DETECTED")
        print("=" * 60)
        for ts, err_msg in error_patterns[:20]:
            print(f"{ts.strftime('%H:%M:%S')} | {err_msg}")
    
    # Diagnosis and recommendations
    print("\n" + "=" * 60)
    print("DIAGNOSIS & RECOMMENDATIONS")
    print("=" * 60)
    
    if not target_post_found:
        print("⚠️  TARGET POST NOT FOUND IN LOGS")
        print("\nPossible issues:")
        print("  1. Sitemap may not include the new blog post URL")
        print("  2. Blog post publication date may not match sitemap lastmod")
        print("  3. Crawler date range filter may be excluding this post")
        print("  4. Sitemap cache may need invalidation")
        print("  5. Blog post may be in draft/unpublished state on staging")
        print("\nRecommended actions:")
        print("  - Verify blog post exists at the URL")
        print("  - Check sitemap XML for the blog post entry")
        print("  - Review crawler date filtering logic")
        print("  - Ensure staging environment has latest content")
        print("  - Clear sitemap cache and re-run crawler")
    else:
        print("✓ Target post WAS found in crawler logs")
        print("  - Review above logs for processing details")
    
    # Detailed log output (last 150 lines for better context)
    print("\n" + "=" * 60)
    print("DETAILED LOG TAIL (Last 150 events)")
    print("=" * 60 + "\n")
    
    for event in response['events'][-150:]:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event['message'].strip()
        
        # Highlight important lines
        prefix = ""
        if target_url in message or target_date in message:
            prefix = "[TARGET] "
        elif 'error' in message.lower() or 'failed' in message.lower():
            prefix = "[ERROR] "
        elif 'sitemap' in message.lower():
            prefix = "[SITEMAP] "
        elif '/blogs/desktop-and-application-streaming/' in message:
            prefix = "[BLOG] "
        
        print(f"{prefix}{timestamp.strftime('%H:%M:%S')} | {message}")
    
except logs_client.exceptions.ResourceNotFoundException:
    print(f"Error: Log group '{log_group}' not found.")
    print("Please verify the log group name and ensure the Lambda function exists.")
except Exception as e:
    print(f"Error retrieving logs: {e}")
    print(f"Error type: {type(e).__name__}")
```