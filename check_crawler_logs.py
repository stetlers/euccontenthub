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
print("CRAWLER LAMBDA LOGS - DIAGNOSTIC TOOL")
print("=" * 80)

# Target blog post URL to investigate
TARGET_URL = "https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/"
TARGET_DATE = "2026-03-02"
TARGET_KEYWORDS = ["workspaces", "graphics", "g6", "gr6", "g6f", "bundles"]

def parse_datetime_from_log(message):
    """Extract datetime from log messages"""
    date_patterns = [
        r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
        r'(\d{2}/\d{2}/\d{4})',  # MM/DD/YYYY
        r'(\d{4}/\d{2}/\d{2})',  # YYYY/MM/DD
    ]
    for pattern in date_patterns:
        match = re.search(pattern, message)
        if match:
            return match.group(1)
    return None

def extract_urls(message):
    """Extract all URLs from a log message"""
    url_pattern = r'https?://[^\s\'"<>]+'
    return re.findall(url_pattern, message)

def check_date_filtering(message, target_date):
    """Check if date filtering is mentioned and validate against target date"""
    date_filter_keywords = ['date filter', 'date range', 'published after', 'published before', 'cutoff date']
    for keyword in date_filter_keywords:
        if keyword in message.lower():
            extracted_date = parse_datetime_from_log(message)
            if extracted_date:
                return True, extracted_date
    return False, None

def analyze_log_events(events):
    """Analyze log events for crawler behavior and potential issues"""
    print(f"\nAnalyzing {len(events)} log events...\n")
    
    # Tracking variables for investigation
    found_target_url = False
    found_target_category = False
    found_target_keywords = {keyword: False for keyword in TARGET_KEYWORDS}
    crawl_errors = []
    processed_urls = []
    filtered_urls = []
    date_filters_detected = []
    url_patterns_detected = []
    category_patterns_detected = []
    scraping_issues = []
    storage_issues = []
    
    for event in events:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event["message"].strip()
        
        # Print all log messages with timestamp
        print(f'{timestamp.strftime("%Y-%m-%d %H:%M:%S")} | {message}')
        
        # Check for target URL
        if TARGET_URL in message:
            found_target_url = True
            print(f"  >>> TARGET URL FOUND: {message}")
        
        # Check for target category
        if "desktop-and-application-streaming" in message.lower():
            found_target_category = True
            category_patterns_detected.append(message)
        
        # Check for target keywords
        message_lower = message.lower()
        for keyword in TARGET_KEYWORDS:
            if keyword in message_lower:
                found_target_keywords[keyword] = True
        
        # Extract and track processed URLs
        urls = extract_urls(message)
        if urls:
            for url in urls:
                if url not in processed_urls:
                    processed_urls.append(url)
        
        # Detect URL pattern matching
        if "url pattern" in message_lower or "pattern match" in message_lower or "regex" in message_lower:
            url_patterns_detected.append(message)
        
        # Detect date filtering
        has_date_filter, detected_date = check_date_filtering(message, TARGET_DATE)
        if has_date_filter:
            date_filters_detected.append({
                'message': message,
                'detected_date': detected_date,
                'timestamp': timestamp
            })
        
        # Detect filtering or skipping
        skip_keywords = ['skip', 'filter', 'ignor', 'exclud', 'reject', 'discard']
        if any(keyword in message_lower for keyword in skip_keywords):
            filtered_urls.append({
                'message': message,
                'timestamp': timestamp
            })
        
        # Detect scraping issues
        scraping_keywords = ['scrape', 'parse', 'extract', 'content']
        if any(keyword in message_lower for keyword in scraping_keywords):
            if any(err in message_lower for err in ['error', 'fail', 'unable', 'could not', 'timeout']):
                scraping_issues.append(message)
        
        # Detect storage/database issues
        storage_keywords = ['store', 'save', 'database', 'dynamo', 's3', 'persist']
        if any(keyword in message_lower for keyword in storage_keywords):
            if any(err in message_lower for err in ['error', 'fail', 'unable', 'could not']):
                storage_issues.append(message)
        
        # Collect errors
        error_indicators = ['error', 'exception', 'fail', 'traceback', 'warning']
        if any(indicator in message_lower for indicator in error_indicators):
            crawl_errors.append({
                'message': message,
                'timestamp': timestamp
            })
    
    # Print comprehensive investigation summary
    print("\n" + "=" * 80)
    print("INVESTIGATION SUMMARY")
    print("=" * 80)
    print(f"Target URL: {TARGET_URL}")
    print(f"Target Date: {TARGET_DATE}")
    print(f"Target Category: desktop-and-application-streaming")
    
    print(f"\n--- Detection Results ---")
    print(f"✓ Target URL found in logs: {found_target_url}")
    print(f"✓ Target category found in logs: {found_target_category}")
    print(f"\n--- Keyword Detection ---")
    for keyword, found in found_target_keywords.items():
        symbol = "✓" if found else "✗"
        print(f"{symbol} '{keyword}': {found}")
    
    print(f"\n--- Crawler Statistics ---")
    print(f"Total URLs processed: {len(processed_urls)}")
    print(f"Total URLs filtered/skipped: {len(filtered_urls)}")
    print(f"Date filters detected: {len(date_filters_detected)}")
    print(f"URL patterns detected: {len(url_patterns_detected)}")
    print(f"Category patterns detected: {len(category_patterns_detected)}")
    print(f"Scraping issues: {len(scraping_issues)}")
    print(f"Storage issues: {len(storage_issues)}")
    print(f"Total errors: {len(crawl_errors)}")
    
    # Show processed URLs
    if processed_urls:
        print(f"\n--- Processed URLs (showing first 20) ---")
        for i, url in enumerate(processed_urls[:20], 1):
            print(f"{i}. {url}")
    
    # Show date filtering details
    if date_filters_detected:
        print(f"\n--- Date Filtering Analysis ---")
        for i, filter_info in enumerate(date_filters_detected, 1):
            print(f"{i}. [{filter_info['timestamp'].strftime('%H:%M:%S')}] {filter_info['message']}")
            if filter_info['detected_date']:
                print(f"   Detected date: {filter_info['detected_date']}")
                print(f"   Target date: {TARGET_DATE}")
                if filter_info['detected_date'] != TARGET_DATE:
                    print(f"   ⚠ DATE MISMATCH - Post may be filtered out!")
    
    # Show URL pattern details
    if url_patterns_detected:
        print(f"\n--- URL Pattern Analysis (showing first 5) ---")
        for i, pattern in enumerate(url_patterns_detected[:5], 1):
            print(f"{i}. {pattern}")
    
    # Show filtered URLs with context
    if filtered_urls:
        print(f"\n--- Filtered/Skipped Entries (showing first 10) ---")
        for i, filtered in enumerate(filtered_urls[:10], 1):
            print(f"{i}. [{filtered['timestamp'].strftime('%H:%M:%S')}] {filtered['message']}")
    
    # Show scraping issues
    if scraping_issues:
        print(f"\n--- Scraping Issues Detected ---")
        for i, issue in enumerate(scraping_issues, 1):
            print(f"{i}. {issue}")
    
    # Show storage issues
    if storage_issues:
        print(f"\n--- Storage/Database Issues Detected ---")
        for i, issue in enumerate(storage_issues, 1):
            print(f"{i}. {issue}")
    
    # Show errors with context
    if crawl_errors:
        print(f"\n--- Errors Detected (showing first 15) ---")
        for i, error in enumerate(crawl_errors[:15], 1):
            print(f"{i}. [{error['timestamp'].strftime('%H:%M:%S')}] {error['message']}")
    
    # Provide detailed recommendations
    print("\n" + "=" * 80)
    print("DIAGNOSTIC RECOMMENDATIONS")
    print("=" * 80)
    
    issues_found = False
    
    if not found_target_url and not any(found_target_keywords.values()):
        print("⚠ CRITICAL: Target blog post not detected in logs")
        print("  Possible causes:")
        print("  → Post may not exist on staging.awseuccontent.com")
        print("  → Crawler may not be accessing the correct feed/sitemap")
        print("  → URL structure may have changed")
        print("  Action: Verify post exists and is accessible")
        issues_found = True
    
    if not found_target_category:
        print("\n⚠ WARNING: Target category 'desktop-and-application-streaming' not found")
        print("  Possible causes:")
        print("  → Category filter may be too restrictive")
        print("  → Crawler configuration may not include this category")
        print("  → RSS feed/sitemap may not contain this category")
        print("  Action: Review crawler category configuration")
        issues_found = True
    
    if date_filters_detected:
        print("\n⚠ WARNING: Date filters detected - verify target date compatibility")
        print("  Action: Check if March 2, 2026 falls within the configured date range")
        issues_found = True
    
    if len(filtered_urls) > len(processed_urls) * 0.5:
        print("\n⚠ WARNING: High filtering rate detected (>50% of entries filtered)")
        print("  Action: Review filtering logic - may be too aggressive")
        issues_found = True
    
    if scraping_issues:
        print("\n⚠ ERROR: Scraping issues detected")
        print("  Action: Review scraping logic and HTML parsing")
        issues_found = True
    
    if storage_issues:
        print("\n⚠ ERROR: Storage/database issues detected")
        print("  Action: Check database connectivity and permissions")
        issues_found = True
    
    if crawl_errors:
        print("\n⚠ ERROR: General errors detected during crawling")
        print("  Action: Investigate error messages above")
        issues_found = True
    
    if not issues_found and not found_target_url:
        print("⚠ No obvious issues detected, but target post not found")
        print("  Recommended deep-dive investigation:")
        print("  → Enable debug logging in crawler")
        print("  → Test crawler with explicit URL")
        print("  → Verify post publication status on staging")
    
    print("\n" + "=" * 80)
    print("ACTIONABLE NEXT STEPS")
    print("=" * 80)
    print("1. Verify blog post exists at staging.awseuccontent.com:")
    print(f"   curl -I {TARGET_URL}")
    print("\n2. Check crawler configuration:")
    print("   - Date range filters (ensure March 2, 2026 is included)")
    print("   - Category filters (ensure desktop-and-application-streaming is enabled)")
    print("   - URL pattern matching (verify regex patterns match target URL)")
    print("\n3. Test crawler directly:")
    print("   aws lambda invoke --function-name aws-blog-crawler --payload '{\"test_url\": \"TARGET_URL\"}' output.json")
    print("\n4. Review crawler code:")
    print("   - Date parsing and filtering logic")
    print("   - URL extraction from feeds/sitemaps")
    print("   - Content scraping selectors")
    print("   - Storage/persistence logic")
    print("\n5. Check data pipeline:")
    print("   - Verify DynamoDB/database entries")
    print("   - Check S3 bucket for scraped content")
    print("   - Review downstream processing logs")
    print("=" * 80)

try:
    print("\nSearching for recent crawler logs...")
    
    # Try last 5 minutes first
    response = logs.filter_log_events(
        logGroupName='/aws/lambda/aws-blog-crawler',
        startTime=int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)
    )
    
    if response['events']:
        print(f"Found logs from last 5 minutes")
        analyze_log_events(response['events'])
    else:
        print("\nNo logs found in last 5 minutes")
        print("Expanding search to last 30 minutes...")
        
        response = logs.filter_log_events(
            logGroupName='/aws/lambda/aws-blog-crawler',
            startTime=int((datetime.now() - timedelta(minutes=30)).timestamp() * 1000)
        )
        
        if response['events']:
            print(f"Found logs from last 30 minutes (showing last 200 events)")
            analyze_log_events(response['events'][-200:])
        else:
            print("No logs found in last 30 minutes either")
            print("\nExpanding search to last 24 hours...")
            
            response = logs.filter_log_events(
                logGroupName='/aws/lambda/aws-blog-crawler',
                startTime=int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)
            )
            
            if response['events']:
                print(f"Found logs from last 24 hours (showing last 200 events)")
                analyze_log_events(response['events'][-200:])
            else:
                print("\n" + "=" * 80)
                print("NO LOGS FOUND - TROUBLESHOOTING")
                print("=" * 80)
                print("\n1. Verify the Lambda function name:")
                print("   aws lambda list-functions --query 'Functions[?contains(FunctionName, `crawler`)].FunctionName'")
                print("\n2. Check if crawler has been invoked recently:")
                print("   aws lambda get-function --function-name aws-blog-crawler")
                print("\n3. Verify CloudWatch Logs exist:")
                print("   aws logs describe-log-groups --log-group-name-prefix '/aws/lambda/'")
                print("\n4. Check IAM permissions:")
                print("   - logs:FilterLogEvents")
                print("   - logs:DescribeLogGroups")
                print("   - logs:GetLogEvents")
                print("\n5. Manually invoke the crawler:")
                print("   aws lambda invoke --function-name aws-blog-crawler output.json")
                print("\n6. Check if crawler is scheduled:")
                print("   aws events list-rules --name-prefix crawler")
                print("\n7. Verify region (currently set to us-east-1)")
                print("=" * 80)
            
except logs.exceptions.ResourceNotFoundException:
    print("\