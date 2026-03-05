```python
"""
Check crawler Lambda logs from the most recent invocation
Enhanced to investigate missing Amazon WorkSpaces blog post detection
"""
import boto3
from datetime import datetime, timedelta
import re

logs = boto3.client('logs', region_name='us-east-1')

print("=" * 80)
print("CRAWLER LAMBDA LOGS (last 5 minutes)")
print("=" * 80)

# Target blog post URL to investigate
TARGET_URL = "https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/"
TARGET_DATE = "2026-03-02"

def analyze_log_events(events):
    """Analyze log events for crawler behavior and potential issues"""
    print(f"\nFound {len(events)} log events\n")
    
    # Tracking variables for investigation
    found_target_url = False
    found_target_category = False
    crawl_errors = []
    processed_urls = []
    filtered_urls = []
    
    for event in events:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event["message"].strip()
        
        # Print all log messages
        print(f'{timestamp.strftime("%H:%M:%S")} | {message}')
        
        # Check for target URL or category
        if "desktop-and-application-streaming" in message.lower():
            found_target_category = True
        
        if "workspaces" in message.lower() and "graphics" in message.lower():
            found_target_url = True
        
        # Extract processed URLs
        if "processing" in message.lower() or "crawling" in message.lower():
            url_match = re.search(r'https?://[^\s]+', message)
            if url_match:
                processed_urls.append(url_match.group(0))
        
        # Detect filtering or skipping
        if "skip" in message.lower() or "filter" in message.lower() or "ignor" in message.lower():
            filtered_urls.append(message)
        
        # Collect errors
        if "error" in message.lower() or "exception" in message.lower() or "fail" in message.lower():
            crawl_errors.append(message)
    
    # Print investigation summary
    print("\n" + "=" * 80)
    print("INVESTIGATION SUMMARY")
    print("=" * 80)
    print(f"Target URL: {TARGET_URL}")
    print(f"Target Date: {TARGET_DATE}")
    print(f"\nFound target category (desktop-and-application-streaming): {found_target_category}")
    print(f"Found target blog post keywords: {found_target_url}")
    print(f"\nTotal URLs processed: {len(processed_urls)}")
    print(f"Total URLs filtered/skipped: {len(filtered_urls)}")
    print(f"Total errors: {len(crawl_errors)}")
    
    if crawl_errors:
        print("\nErrors detected:")
        for error in crawl_errors[:10]:
            print(f"  - {error}")
    
    if filtered_urls:
        print("\nFiltered/Skipped entries (showing first 10):")
        for filtered in filtered_urls[:10]:
            print(f"  - {filtered}")
    
    # Provide recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    if not found_target_category:
        print("⚠ The 'desktop-and-application-streaming' category was not found in logs.")
        print("  → Check if the crawler is configured to crawl this blog category")
        print("  → Verify the RSS feed or sitemap includes this category")
    
    if not found_target_url:
        print("⚠ The target blog post about WorkSpaces Graphics bundles was not detected.")
        print("  → Check date filters in crawler (post date: March 2, 2026)")
        print("  → Verify the blog post is published on staging.awseuccontent.com")
        print("  → Check if URL pattern matches crawler configuration")
        print("  → Review content filtering logic (keywords, categories)")
    
    if crawl_errors:
        print("⚠ Errors were detected during crawling - investigate above error messages")
    
    print("\nNext steps:")
    print("1. Verify blog post exists at: staging.awseuccontent.com")
    print("2. Check crawler configuration for date range filters")
    print("3. Review category/URL pattern matching logic")
    print("4. Test crawler with explicit URL if available")
    print("=" * 80)

try:
    response = logs.filter_log_events(
        logGroupName='/aws/lambda/aws-blog-crawler',
        startTime=int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)
    )
    
    if response['events']:
        analyze_log_events(response['events'])
    else:
        print("\nNo logs found in last 5 minutes")
        print("Checking last 30 minutes...")
        
        response = logs.filter_log_events(
            logGroupName='/aws/lambda/aws-blog-crawler',
            startTime=int((datetime.now() - timedelta(minutes=30)).timestamp() * 1000)
        )
        
        if response['events']:
            # Show last 100 events for better investigation
            analyze_log_events(response['events'][-100:])
        else:
            print("No logs found in last 30 minutes either")
            print("\nTroubleshooting tips:")
            print("1. Verify the Lambda function name is 'aws-blog-crawler'")
            print("2. Check if crawler has been invoked recently")
            print("3. Verify IAM permissions to read CloudWatch Logs")
            print("4. Try manually invoking the crawler Lambda function")
            
except Exception as e:
    print(f'Error accessing CloudWatch Logs: {e}')
    print("\nPossible causes:")
    print("- IAM permissions issue (logs:FilterLogEvents)")
    print("- Incorrect log group name")
    print("- Region mismatch (currently set to us-east-1)")
    print("- Network connectivity issue")
```