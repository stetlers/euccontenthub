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
    
    # Enhanced tracking for date filtering diagnostics
    date_filter_events = []
    sitemap_entries = []
    url_parsing_events = []
    metadata_parsing_events = []
    posts_by_date = {}
    date_range_info = {}
    
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
        
        # Track sitemap entries with dates
        if 'lastmod' in message.lower() or '<lastmod>' in message:
            sitemap_entries.append((timestamp, message))
        
        # Track date filtering logic
        if any(keyword in message.lower() for keyword in ['date filter', 'filtering by date', 'date range', 'cutoff date', 'date comparison']):
            date_filter_events.append((timestamp, message))
        
        # Track date range configuration
        if any(keyword in message.lower() for keyword in ['start_date', 'end_date', 'date_range', 'lookback', 'days_back']):
            date_range_info[timestamp] = message
        
        # Track URL parsing events
        if any(keyword in message.lower() for keyword in ['parsing url', 'extracting url', 'url detected', 'found url']):
            url_parsing_events.append((timestamp, message))
        
        # Track metadata parsing events
        if any(keyword in message.lower() for keyword in ['parsing metadata', 'extracting metadata', 'publication date', 'pubdate', 'article date']):
            metadata_parsing_events.append((timestamp, message))
        
        # Extract and categorize posts by date
        date_match = re.search(r'20\d{2}-\d{2}-\d{2}', message)
        if date_match and '/blogs/' in message:
            extracted_date = date_match.group(0)
            if extracted_date not in posts_by_date:
                posts_by_date[extracted_date] = []
            posts_by_date[extracted_date].append(message)
        
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
    print(f"Date filtering events: {len(date_filter_events)}")
    print(f"URL parsing events: {len(url_parsing_events)}")
    print(f"Metadata parsing events: {len(metadata_parsing_events)}")
    print(f"Sitemap entries with dates: {len(sitemap_entries)}")
    
    # Display date range configuration
    if date_range_info:
        print("\n" + "=" * 60)
        print("DATE RANGE CONFIGURATION")
        print("=" * 60)
        for ts, info in list(date_range_info.items())[:10]:
            print(f"{ts.strftime('%H:%M:%S')} | {info}")
    
    # Display posts categorized by date
    if posts_by_date:
        print("\n" + "=" * 60)
        print("POSTS BY DATE")
        print("=" * 60)
        sorted_dates = sorted(posts_by_date.keys(), reverse=True)
        for post_date in sorted_dates[:15]:
            print(f"\n{post_date} ({len(posts_by_date[post_date])} posts):")
            for post in posts_by_date[post_date][:5]:
                print(f"  - {post[:120]}{'...' if len(post) > 120 else ''}")
        
        # Check if target date is present
        if target_date in posts_by_date:
            print(f"\n✓ Target date {target_date} found with {len(posts_by_date[target_date])} posts")
        else:
            print(f"\n⚠️  Target date {target_date} NOT found in processed posts")
    
    # Display date filtering events
    if date_filter_events:
        print("\n" + "=" * 60)
        print("DATE FILTERING EVENTS")
        print("=" * 60)
        for ts, event in date_filter_events[:20]:
            print(f"{ts.strftime('%H:%M:%S')} | {event}")
    
    # Display URL parsing events
    if url_parsing_events:
        print("\n" + "=" * 60)
        print("URL PARSING EVENTS")
        print("=" * 60)
        for ts, event in url_parsing_events[:20]:
            print(f"{ts.strftime('%H:%M:%S')} | {event}")
    
    # Display metadata parsing events
    if metadata_parsing_events:
        print("\n" + "=" * 60)
        print("METADATA PARSING EVENTS")
        print("=" * 60)
        for ts, event in metadata_parsing_events[:20]:
            print(f"{ts.strftime('%H:%M:%S')} | {event}")
    
    # Display sitemap information
    if sitemap_urls_found:
        print("\n" + "=" * 60)
        print("SITEMAPS PROCESSED")
        print("=" * 60)
        for sitemap in sitemap_urls_found[:10]:
            print(f"  - {sitemap}")
    
    # Display sitemap entries with dates
    if sitemap_entries:
        print("\n" + "=" * 60)
        print("SITEMAP ENTRIES WITH DATES (Sample)")
        print("=" * 60)
        for ts, entry in sitemap_entries[:30]:
            # Check if this entry contains target date or URL
            is_target = target_date in entry or target_url in entry
            prefix = "[TARGET] " if is_target else ""
            print(f"{prefix}{ts.strftime('%H:%M:%S')} | {entry[:150]}{'...' if len(entry) > 150 else ''}")
    
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
    
    # Enhanced diagnosis and recommendations
    print("\n" + "=" * 60)
    print("DIAGNOSIS & RECOMMENDATIONS")
    print("=" * 60)
    
    if not target_post_found:
        print("⚠️  TARGET POST NOT FOUND IN LOGS")
        print("\nPossible issues:")
        print("  1. Sitemap may not include the new blog post URL")
        print("  2. Blog post publication date may not match sitemap lastmod")
        print("  3. Crawler date range filter may be excluding this post")
        print("  4. Date comparison logic may have timezone issues")
        print("  5. URL parsing may be failing for this specific post format")
        print("  6. Metadata extraction may not be capturing the publication date")
        print("  7. Sitemap cache may need invalidation")
        print("  8. Blog post may be in draft/unpublished state on staging")
        
        # Provide specific recommendations based on collected data
        print("\nSpecific findings:")
        if target_date not in posts_by_date:
            print(f"  ⚠️  No posts found for date {target_date}")
            print("     → Check if date filtering is too restrictive")
            print("     → Verify sitemap contains entries with this date")
        
        if not date_filter_events:
            print("  ⚠️  No date filtering events detected")
            print("     → Date filtering logic may not be logging properly")
            print("     → Verify date filter code is being executed")
        
        if not url_parsing_events:
            print("  ⚠️  No URL parsing events detected")
            print("     → URL detection logic may not be logging")
            print("     → Check if URL extraction code is working")
        
        print("\nRecommended actions:")
        print("  1. Verify blog post exists at the URL in staging environment")
        print("  2. Check sitemap XML directly for the blog post entry")
        print("  3. Review crawler date filtering logic and cutoff dates")
        print("  4. Examine date parsing for timezone handling (UTC vs local)")
        print("  5. Test URL pattern matching against the target URL")
        print("  6. Verify metadata extraction from blog post HTML")
        print("  7. Check if sitemap lastmod date matches publication date")
        print("  8. Clear sitemap cache and re-run crawler")
        print("  9. Add debug logging to date filtering and URL parsing functions")
        print(" 10. Verify the crawler's lookback period includes March 2, 2026")
    else:
        print("✓ Target post WAS found in crawler logs")
        print("  - Review above logs for processing details")
        print("  - Check if post was filtered out later in the pipeline")
    
    # Date range analysis
    if posts_by_date:
        print("\nDate range analysis:")
        dates = sorted(posts_by_date.keys())
        if dates:
            print(f"  Earliest post date: {dates[0]}")
            print(f"  Latest post date: {dates[-1]}")
            print(f"  Target date {target_date} is {'within' if dates[0] <= target_date <= dates[-1] else 'OUTSIDE'} range")
    
    # Detailed log output (last 150 lines for better context)
    print("\n" + "=" * 60)
    print("DETAILED LOG TAIL (Last 150 events)")
    print("=" * 60 + "\n")
    
    for event in response['events'][-150:]:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event['message'].strip()
        
        # Highlight important lines with enhanced categorization
        prefix = ""
        if target_url in message or target_date in message:
            prefix = "[TARGET] "
        elif 'error' in message.lower() or 'failed' in message.lower():
            prefix = "[ERROR] "
        elif any(keyword in message.lower() for keyword in ['date filter', 'filtering by date', 'date range']):
            prefix = "[DATE-FILTER] "
        elif 'sitemap' in message.lower():
            prefix = "[SITEMAP] "
        elif 'parsing' in message.lower() or 'extracting' in message.lower():
            prefix = "[PARSING] "
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