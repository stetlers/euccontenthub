```python
import boto3
from datetime import datetime, timedelta
import re

logs_client = boto3.client('logs', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

print("=" * 60)
print("Detailed Sitemap Crawler Logs - Enhanced Debugging")
print("=" * 60)

log_group = '/aws/lambda/aws-blog-crawler'
# Extended time window to capture more historical logs
start_time = int((datetime.now() - timedelta(hours=6)).timestamp() * 1000)

# Target blog post URL to track
target_url = "amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles"
target_date = "2026-03-02"
target_date_variations = ["2026-03-02", "2026/03/02", "03/02/2026", "March 2, 2026", "Mar 2, 2026"]

# Check DynamoDB staging table for the post
print("\n" + "=" * 60)
print("CHECKING STAGING DYNAMODB TABLE")
print("=" * 60)

try:
    table_name = 'aws-blog-posts-staging'
    table = dynamodb.Table(table_name)
    
    # Try to find the target post in DynamoDB
    print(f"Scanning table: {table_name}")
    print(f"Looking for URL fragment: {target_url}")
    
    response = table.scan(
        FilterExpression='contains(#url, :url_fragment) OR contains(title, :title_fragment)',
        ExpressionAttributeNames={'#url': 'url'},
        ExpressionAttributeValues={
            ':url_fragment': target_url,
            ':title_fragment': 'WorkSpaces'
        },
        Limit=100
    )
    
    found_in_db = False
    if response.get('Items'):
        print(f"\n✓ Found {len(response['Items'])} matching items in DynamoDB:")
        for item in response['Items']:
            if target_url in item.get('url', ''):
                found_in_db = True
                print(f"\n[TARGET POST FOUND IN DB]")
            print(f"  Title: {item.get('title', 'N/A')}")
            print(f"  URL: {item.get('url', 'N/A')}")
            print(f"  Date: {item.get('publication_date', 'N/A')}")
            print(f"  Timestamp: {item.get('timestamp', 'N/A')}")
            print()
    else:
        print("\n⚠️  No matching posts found in DynamoDB staging table")
    
    if not found_in_db:
        print(f"\n⚠️  Target post '{target_url}' NOT found in DynamoDB")
        print("     → Post may not have been stored by crawler")
        print("     → Indicates crawler filtering or processing issue")
    
    # Check for recent posts around target date
    print(f"\n\nChecking for posts near target date ({target_date})...")
    response = table.scan(
        FilterExpression='begins_with(publication_date, :date_prefix)',
        ExpressionAttributeValues={
            ':date_prefix': '2026-03'
        },
        Limit=50
    )
    
    if response.get('Items'):
        print(f"Found {len(response['Items'])} posts in March 2026:")
        for item in sorted(response['Items'], key=lambda x: x.get('publication_date', ''), reverse=True)[:20]:
            print(f"  {item.get('publication_date', 'N/A')} | {item.get('title', 'N/A')[:80]}")
    else:
        print("⚠️  No posts found for March 2026")
        print("     → Date filtering may be too restrictive")
        print("     → Crawler may not be processing recent dates")

except dynamodb.meta.client.exceptions.ResourceNotFoundException:
    print(f"⚠️  DynamoDB table '{table_name}' not found")
    print("     → Verify table name for staging environment")
except Exception as e:
    print(f"Error checking DynamoDB: {e}")

try:
    response = logs_client.filter_log_events(
        logGroupName=log_group,
        startTime=start_time,
        filterPattern=''
    )
    
    print(f"\n\n{'=' * 60}")
    print(f"CLOUDWATCH LOGS ANALYSIS")
    print(f"{'=' * 60}")
    print(f"Total log events: {len(response['events'])}")
    print(f"Time range: {datetime.fromtimestamp(start_time/1000)} to {datetime.now()}\n")
    
    # Statistics tracking
    sitemap_urls_found = []
    blog_posts_processed = []
    workspaces_posts = []
    target_post_found = False
    error_patterns = []
    
    # Enhanced tracking for date filtering diagnostics
    date_filter_events = []
    date_comparison_events = []
    sitemap_entries = []
    url_parsing_events = []
    metadata_parsing_events = []
    posts_by_date = {}
    date_range_info = {}
    crawler_config = {}
    lambda_invocations = []
    sitemap_fetch_events = []
    html_fetch_events = []
    date_parsing_errors = []
    
    # Track future dates specifically
    future_date_events = []
    march_2026_events = []
    
    print("=" * 60)
    print("SEARCHING FOR TARGET POST")
    print("=" * 60)
    print(f"Target URL fragment: {target_url}")
    print(f"Target date: {target_date}")
    print(f"Date variations: {', '.join(target_date_variations)}\n")
    
    # Analyze all events for patterns
    for event in response['events']:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event['message'].strip()
        
        # Track Lambda invocations
        if 'START RequestId:' in message or 'Lambda function invoked' in message.lower():
            lambda_invocations.append((timestamp, message))
        
        # Track crawler configuration
        if any(keyword in message.lower() for keyword in ['config', 'configuration', 'parameter', 'environment variable']):
            if any(key in message.lower() for key in ['days_back', 'lookback', 'date_range', 'cutoff', 'filter_enabled']):
                crawler_config[timestamp] = message
        
        # Track sitemap fetching
        if any(keyword in message.lower() for keyword in ['fetching sitemap', 'downloading sitemap', 'retrieving sitemap', 'sitemap url:', 'sitemap requested']):
            sitemap_fetch_events.append((timestamp, message))
        
        # Track sitemap processing
        if 'sitemap' in message.lower() and ('processing' in message.lower() or 'parsing' in message.lower()):
            sitemap_urls_found.append(message)
        
        # Track HTML fetching
        if any(keyword in message.lower() for keyword in ['fetching html', 'downloading page', 'retrieving content', 'http get', 'requesting url']):
            html_fetch_events.append((timestamp, message))
        
        # Track sitemap entries with dates
        if 'lastmod' in message.lower() or '<lastmod>' in message or '<loc>' in message:
            sitemap_entries.append((timestamp, message))
        
        # Track date filtering logic with enhanced patterns
        if any(keyword in message.lower() for keyword in ['date filter', 'filtering by date', 'date range', 'cutoff date', 'date comparison', 'before cutoff', 'after cutoff', 'skipping old', 'skipping future']):
            date_filter_events.append((timestamp, message))
        
        # Track specific date comparisons
        if any(keyword in message.lower() for keyword in ['comparing date', 'date check', 'date validation', 'date is before', 'date is after']):
            date_comparison_events.append((timestamp, message))
        
        # Track date parsing errors
        if any(keyword in message.lower() for keyword in ['date parse error', 'invalid date', 'failed to parse date', 'date format error']):
            date_parsing_errors.append((timestamp, message))
        
        # Track date range configuration
        if any(keyword in message.lower() for keyword in ['start_date', 'end_date', 'date_range', 'lookback', 'days_back', 'cutoff_date']):
            date_range_info[timestamp] = message
        
        # Track URL parsing events
        if any(keyword in message.lower() for keyword in ['parsing url', 'extracting url', 'url detected', 'found url', 'url pattern']):
            url_parsing_events.append((timestamp, message))
        
        # Track metadata parsing events
        if any(keyword in message.lower() for keyword in ['parsing metadata', 'extracting metadata', 'publication date', 'pubdate', 'article date', 'date from html', 'meta tag']):
            metadata_parsing_events.append((timestamp, message))
        
        # Track future date handling
        if '2026' in message or 'future' in message.lower():
            future_date_events.append((timestamp, message))
            if '2026-03' in message or 'march 2026' in message.lower():
                march_2026_events.append((timestamp, message))
        
        # Extract and categorize posts by date - enhanced pattern matching
        date_match = re.search(r'20\d{2}-\d{2}-\d{2}', message)
        if date_match:
            extracted_date = date_match.group(0)
            if extracted_date not in posts_by_date:
                posts_by_date[extracted_date] = []
            posts_by_date[extracted_date].append(message)
        
        # Track blog post URLs being processed
        if '/blogs/desktop-and-application-streaming/' in message or 'aws.amazon.com/blogs' in message:
            blog_posts_processed.append(message)
            if 'workspaces' in message.lower():
                workspaces_posts.append(message)
        
        # Check for target post with multiple variations
        if target_url in message or any(date_var in message for date_var in target_date_variations):
            target_post_found = True
            print(f"[FOUND] {timestamp.strftime('%Y-%m-%d %H:%M:%S')} | {message}")
        
        # Track errors with enhanced patterns
        if any(keyword in message.lower() for keyword in ['error', 'failed', 'exception', 'timeout', 'traceback', 'warning']):
            error_patterns.append((timestamp, message))
    
    # Summary statistics
    print("\n" + "=" * 60)
    print("CRAWLER STATISTICS")
    print("=" * 60)
    print(f"Lambda invocations: {len(lambda_invocations)}")
    print(f"Sitemap fetch attempts: {len(sitemap_fetch_events)}")
    print(f"Sitemaps processed: {len(sitemap_urls_found)}")
    print(f"Sitemap entries detected: {len(sitemap_entries)}")
    print(f"HTML pages fetched: {len(html_fetch_events)}")
    print(f"Blog posts found: {len(blog_posts_processed)}")
    print(f"WorkSpaces-related posts: {len(workspaces_posts)}")
    print(f"Target post detected: {'YES' if target_post_found else 'NO'}")
    print(f"Errors encountered: {len(error_patterns)}")
    print(f"Date filtering events: {len(date_filter_events)}")
    print(f"Date comparison events: {len(date_comparison_events)}")
    print(f"Date parsing errors: {len(date_parsing_errors)}")
    print(f"URL parsing events: {len(url_parsing_events)}")
    print(f"Metadata parsing events: {len(metadata_parsing_events)}")
    print(f"Future date events (2026): {len(future_date_events)}")
    print(f"March 2026 specific events: {len(march_2026_events)}")
    
    # Display Lambda invocations
    if lambda_invocations:
        print("\n" + "=" * 60)
        print("LAMBDA INVOCATIONS")
        print("=" * 60)
        for ts, inv in lambda_invocations[-10:]:
            print(f"{ts.strftime('%Y-%m-%d %H:%M:%S')} | {inv}")
    
    # Display crawler configuration
    if crawler_config:
        print("\n" + "=" * 60)
        print("CRAWLER CONFIGURATION")
        print("=" * 60)
        for ts, config in list(crawler_config.items())[:15]:
            print(f"{ts.strftime('%H:%M:%S')} | {config}")
    
    # Display date range configuration
    if date_range_info:
        print("\n" + "=" * 60)
        print("DATE RANGE CONFIGURATION")
        print("=" * 60)
        for ts, info in list(date_range_info.items())[:15]:
            print(f"{ts.strftime('%H:%M:%S')} | {info}")
    
    # Display sitemap fetch events
    if sitemap_fetch_events:
        print("\n" + "=" * 60)
        print("SITEMAP FETCH EVENTS")
        print("=" * 60)
        for ts, event in sitemap_fetch_events[:15]:
            print(f"{ts.strftime('%H:%M:%S')} | {event}")
    
    # Display posts categorized by date
    if posts_by_date:
        print("\n" + "=" * 60)
        print("POSTS BY DATE")
        print("=" * 60)
        sorted_dates = sorted(posts_by_date.keys(), reverse=True)
        for post_date in sorted_dates[:20]:
            marker = " ← TARGET DATE" if post_date == target_date else ""
            print(f"\n{post_date} ({len(posts_by_date[post_date])} posts){marker}:")
            for post in posts_by_date[post_date][:5]:
                print(f"  - {post[:120]}{'...' if len(post) > 120 else ''}")
        
        # Check if target date is present
        if target_date in posts_by_date:
            print(f"\n✓ Target date {target_date} found with {len(posts_by_date[target_date])} posts")
        else:
            print(f"\n⚠️  Target date {target_date} NOT found in processed posts")
    
    # Display March 2026 events
    if march_2026_events:
        print("\n" + "=" * 60)
        print("MARCH 2026 EVENTS")
        print("=" * 60)
        for ts, event in march_2026_events[:30]:
            print(f"{ts.strftime('%H:%M:%S')} | {event}")
    
    # Display date filtering events
    if date_filter_events:
        print("\n" + "=" * 60)
        print("DATE FILTERING EVENTS")
        print("=" * 60)
        for ts, event in date_filter_events[:25]:
            print(f"{ts.strftime('%H:%M:%S')} | {event}")
    
    # Display date comparison events
    if date_comparison_events:
        print("\n" + "=" * 60)
        print("DATE COMPARISON EVENTS")
        print("=" * 60)
        for ts, event in date_comparison_events[:25]:
            print(f"{ts.strftime('%H:%M:%S')} | {event}")
    
    # Display date parsing errors
    if date_parsing_errors:
        print("\n" + "=" * 60)
        print("DATE PARSING ERRORS")
        print