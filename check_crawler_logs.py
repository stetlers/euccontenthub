```python
"""
Check crawler Lambda logs from the most recent invocation
Enhanced to investigate missing Amazon WorkSpaces blog post detection
"""
import boto3
from datetime import datetime, timedelta
import re
import json

logs = boto3.client('logs', region_name='us-east-1')

print("=" * 80)
print("CRAWLER LAMBDA LOGS INVESTIGATION")
print("=" * 80)

# Target blog post URL to investigate
TARGET_URL = "https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/"
TARGET_DATE = "2026-03-02"
TARGET_TITLE = "Amazon WorkSpaces launches Graphics G6, Gr6, and G6f bundles"

def parse_date_from_message(message):
    """Extract and parse dates from log messages"""
    date_patterns = [
        r'\b(\d{4}-\d{2}-\d{2})\b',  # YYYY-MM-DD
        r'\b(\d{2}/\d{2}/\d{4})\b',  # MM/DD/YYYY
        r'\b(March\s+\d{1,2},\s+\d{4})\b',  # March 2, 2026
        r'\b(Mar\s+\d{1,2},\s+\d{4})\b',  # Mar 2, 2026
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def analyze_log_events(events):
    """Analyze log events for crawler behavior and potential issues"""
    print(f"\nAnalyzing {len(events)} log events\n")
    print("-" * 80)
    
    # Tracking variables for investigation
    found_target_url = False
    found_target_category = False
    found_target_date = False
    crawl_errors = []
    processed_urls = []
    filtered_urls = []
    date_filters = []
    category_filters = []
    processed_dates = []
    
    for event in events:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event["message"].strip()
        
        # Print all log messages
        print(f'{timestamp.strftime("%Y-%m-%d %H:%M:%S")} | {message}')
        
        # Check for target URL or category
        if "desktop-and-application-streaming" in message.lower():
            found_target_category = True
            category_filters.append(message)
        
        # Check for target post by title or keywords
        if "workspaces" in message.lower() and ("graphics" in message.lower() or "g6" in message.lower()):
            found_target_url = True
        
        # Check for target date
        extracted_date = parse_date_from_message(message)
        if extracted_date:
            processed_dates.append(extracted_date)
            if TARGET_DATE in extracted_date or "2026-03-02" in message or "March 2, 2026" in message or "03/02/2026" in message:
                found_target_date = True
        
        # Extract processed URLs
        if "processing" in message.lower() or "crawling" in message.lower() or "fetched" in message.lower() or "found" in message.lower():
            url_match = re.search(r'https?://[^\s]+', message)
            if url_match:
                processed_urls.append(url_match.group(0))
        
        # Detect filtering or skipping with detailed reason
        if "skip" in message.lower() or "filter" in message.lower() or "ignor" in message.lower() or "exclud" in message.lower():
            filtered_urls.append(message)
            # Check if date filtering is occurring
            if "date" in message.lower() or "old" in message.lower() or "recent" in message.lower():
                date_filters.append(message)
        
        # Collect errors
        if "error" in message.lower() or "exception" in message.lower() or "fail" in message.lower():
            crawl_errors.append(message)
    
    # Print investigation summary
    print("\n" + "=" * 80)
    print("INVESTIGATION SUMMARY")
    print("=" * 80)
    print(f"Target URL: {TARGET_URL}")
    print(f"Target Title: {TARGET_TITLE}")
    print(f"Target Date: {TARGET_DATE}")
    print(f"\n{'='*40}")
    print(f"Detection Status:")
    print(f"{'='*40}")
    print(f"✓ Found target category (desktop-and-application-streaming): {found_target_category}")
    print(f"✓ Found target blog post keywords (WorkSpaces + Graphics/G6): {found_target_url}")
    print(f"✓ Found target date (2026-03-02): {found_target_date}")
    
    print(f"\n{'='*40}")
    print(f"Statistics:")
    print(f"{'='*40}")
    print(f"Total URLs processed: {len(processed_urls)}")
    print(f"Total URLs filtered/skipped: {len(filtered_urls)}")
    print(f"Date-related filters: {len(date_filters)}")
    print(f"Unique dates found: {len(set(processed_dates))}")
    print(f"Total errors: {len(crawl_errors)}")
    
    if crawl_errors:
        print(f"\n{'='*40}")
        print("Errors Detected:")
        print(f"{'='*40}")
        for error in crawl_errors[:10]:
            print(f"  ⚠ {error}")
    
    if date_filters:
        print(f"\n{'='*40}")
        print("Date-Related Filters Applied:")
        print(f"{'='*40}")
        for df in date_filters[:10]:
            print(f"  📅 {df}")
    
    if filtered_urls:
        print(f"\n{'='*40}")
        print("Filtered/Skipped Entries (first 15):")
        print(f"{'='*40}")
        for filtered in filtered_urls[:15]:
            print(f"  ⊘ {filtered}")
    
    if processed_urls:
        print(f"\n{'='*40}")
        print("Sample Processed URLs (first 10):")
        print(f"{'='*40}")
        for url in processed_urls[:10]:
            print(f"  → {url}")
    
    if processed_dates:
        unique_dates = sorted(set(processed_dates))
        print(f"\n{'='*40}")
        print(f"Dates Found in Logs (first 10):")
        print(f"{'='*40}")
        for date in unique_dates[:10]:
            print(f"  📅 {date}")
    
    # Provide recommendations
    print("\n" + "=" * 80)
    print("ROOT CAUSE ANALYSIS & RECOMMENDATIONS")
    print("=" * 80)
    
    recommendations = []
    
    if not found_target_category:
        recommendations.append({
            "severity": "HIGH",
            "issue": "The 'desktop-and-application-streaming' category was not found in logs",
            "actions": [
                "Check if the crawler is configured to crawl this blog category",
                "Verify the RSS feed or sitemap includes this category",
                "Review blog category whitelist/blacklist configuration",
                "Check if category URL pattern matches expected format"
            ]
        })
    
    if not found_target_url:
        recommendations.append({
            "severity": "HIGH",
            "issue": "The target blog post about WorkSpaces Graphics bundles was not detected",
            "actions": [
                "Verify the blog post is published and accessible on staging.awseuccontent.com",
                "Check if URL pattern matches crawler configuration",
                "Review content filtering logic (keywords, categories, tags)",
                "Verify post is not in excluded categories or patterns"
            ]
        })
    
    if not found_target_date and date_filters:
        recommendations.append({
            "severity": "CRITICAL",
            "issue": "Target date (2026-03-02) not found but date filters are active",
            "actions": [
                "LIKELY ROOT CAUSE: Date range filter is excluding March 2, 2026",
                "Check crawler configuration for date range settings (e.g., only_recent_posts, days_back)",
                "Verify current date/time is correct (may be filtering future dates)",
                "Review date parsing logic - ensure 2026 dates are handled correctly",
                "Check if there's a 'future date' filter preventing crawling of posts dated in 2026"
            ]
        })
    elif not found_target_date:
        recommendations.append({
            "severity": "HIGH",
            "issue": "Target date (2026-03-02) not found in any processed content",
            "actions": [
                "Check if the blog post has the correct publication date metadata",
                "Verify date format in blog post matches expected formats",
                "Review date extraction logic in crawler code",
                "Ensure blog post is not draft/scheduled status"
            ]
        })
    
    if crawl_errors:
        recommendations.append({
            "severity": "MEDIUM",
            "issue": f"{len(crawl_errors)} errors detected during crawling",
            "actions": [
                "Review error messages above for specific failure reasons",
                "Check network connectivity to staging.awseuccontent.com",
                "Verify authentication/authorization for staging environment",
                "Check for rate limiting or timeout issues"
            ]
        })
    
    if len(processed_urls) == 0:
        recommendations.append({
            "severity": "CRITICAL",
            "issue": "No URLs were processed by the crawler",
            "actions": [
                "CRITICAL: Crawler may not be running or configured correctly",
                "Verify crawler source configuration (RSS feed, sitemap, or API)",
                "Check if crawler is being invoked with correct parameters",
                "Review crawler entry point and initialization code"
            ]
        })
    
    # Print recommendations
    for i, rec in enumerate(recommendations, 1):
        print(f"\n[{rec['severity']}] Issue #{i}: {rec['issue']}")
        print(f"Actions to take:")
        for action in rec['actions']:
            print(f"  → {action}")
    
    # Final action plan
    print("\n" + "=" * 80)
    print("IMMEDIATE ACTION PLAN")
    print("=" * 80)
    print("\n1. VERIFY BLOG POST EXISTS")
    print("   - Access staging.awseuccontent.com directly")
    print(f"   - Confirm post titled '{TARGET_TITLE}' exists")
    print(f"   - Verify publication date is {TARGET_DATE}")
    
    print("\n2. CHECK CRAWLER CONFIGURATION")
    print("   - Review environment variables: DATE_FILTER, DAYS_BACK, FUTURE_POSTS")
    print("   - Check category filters and URL patterns")
    print("   - Verify staging environment configuration")
    
    print("\n3. INVESTIGATE DATE FILTERING (PRIMARY SUSPECT)")
    print("   - Look for date range restrictions in crawler code")
    print("   - Check if crawler is filtering out 2026 dates as 'future'")
    print("   - Review date comparison logic (ensure it handles staging dates)")
    print("   - Verify system time on Lambda execution environment")
    
    print("\n4. TEST MANUALLY")
    print("   - Invoke crawler with specific URL if supported")
    print("   - Test with date filters disabled")
    print("   - Check RSS feed directly for the post")
    
    print("\n5. REVIEW CODE SECTIONS")
    print("   - Date parsing and filtering logic")
    print("   - Category/URL pattern matching")
    print("   - Content filtering and exclusion rules")
    print("   - Post metadata extraction")
    
    print("\n" + "=" * 80)

try:
    # Try last 5 minutes first
    response = logs.filter_log_events(
        logGroupName='/aws/lambda/aws-blog-crawler',
        startTime=int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)
    )
    
    if response['events']:
        analyze_log_events(response['events'])
    else:
        print("\nNo logs found in last 5 minutes")
        print("Expanding search to last 60 minutes...\n")
        
        response = logs.filter_log_events(
            logGroupName='/aws/lambda/aws-blog-crawler',
            startTime=int((datetime.now() - timedelta(minutes=60)).timestamp() * 1000)
        )
        
        if response['events']:
            # Show last 200 events for thorough investigation
            analyze_log_events(response['events'][-200:])
        else:
            print("No logs found in last 60 minutes")
            print("\nExpanding search to last 24 hours...\n")
            
            response = logs.filter_log_events(
                logGroupName='/aws/lambda/aws-blog-crawler',
                startTime=int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)
            )
            
            if response['events']:
                print(f"Found {len(response['events'])} events in last 24 hours")
                analyze_log_events(response['events'][-200:])
            else:
                print("\n" + "=" * 80)
                print("NO LOGS FOUND - CRAWLER NOT RUNNING")
                print("=" * 80)
                print("\nTroubleshooting steps:")
                print("1. ✓ Verify the Lambda function name is 'aws-blog-crawler'")
                print("2. ✓ Check if crawler has been invoked recently:")
                print("   - Go to Lambda console → aws-blog-crawler → Monitor → Invocations")
                print("3. ✓ Verify crawler is scheduled (EventBridge/CloudWatch Events)")
                print("4. ✓ Check IAM permissions for CloudWatch Logs")
                print("5. ✓ Try manually invoking the crawler Lambda function")
                print("6. ✓ Verify CloudWatch Logs retention policy hasn't deleted logs")
                print("\nPossible root causes:")
                print("  - Crawler is not scheduled or trigger is disabled")
                print("  - Lambda function has been deleted or renamed")
                print("  - Logging is disabled in the Lambda function")
                print("  - Log group has been deleted or changed")
            
except logs.exceptions.ResourceNotFoundException as e:
    print(f"\n{'='*80}")
    print("ERROR: Log Group Not Found")
    print(f"{'='*80}")
    print(f"The log group '/aws/lambda/aws-blog-crawler' does not exist")
    print("\nTroubleshooting steps:")
    print("1. List all Lambda log groups to find the correct name:")
    print("   aws logs describe-log-groups --log-group-name-prefix '/aws/lambda/'")
    print("2. Verify the Lambda function exists and is named correctly")
    print("3. Check if logging is enabled for the Lambda function")
    print("4. Verify you're in the correct AWS region (currently: us-east-1)")

except Exception as e:
    print(f"\n{'='*80}")
    print("ERROR: Failed to Access CloudWatch Logs")
    print(f"{'='*80}")
    print(f"Error: {str(e)}")
    print(f"Error Type: {type(e).__name__}")
    print("\nPossible causes:")
    print("- IAM permissions issue (logs:FilterLogEvents, logs:DescribeLogGroups)")
    print("- Incorrect log group name")
    print("- Region mismatch (currently set to us-east-1)")
    print("- Network connectivity issue")
    print("- AWS credentials not configured or expired")
    print("\nTo fix:")
    print("1. Verify AWS credentials: aws sts get-caller-identity")
    print("2. Check IAM policy includes logs:FilterLogEvents permission")
    print("3. Confirm correct region in AWS configuration")
```