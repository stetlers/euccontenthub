```python
import boto3
from datetime import datetime, timedelta
import json
import re

logs_client = boto3.client('logs', region_name='us-east-1')

print("="*80)
print("CHECKING ECS SELENIUM CRAWLER LOGS - DEEP INVESTIGATION MODE")
print("="*80)

# Get logs from the last 6 hours for more comprehensive investigation
start_time = int((datetime.now() - timedelta(hours=6)).timestamp() * 1000)

# Target blog post details for investigation
TARGET_POST_TITLE = "Amazon WorkSpaces launches Graphics G6, Gr6, and G6f bundles"
TARGET_POST_DATE = "March 2, 2026"
TARGET_STAGING_URL = "staging.awseuccontent.com"
TARGET_BLOG_CATEGORY = "desktop-and-application-streaming"
TARGET_KEYWORDS = ["workspaces", "g6", "gr6", "g6f", "graphics", "desktop-and-application-streaming"]

print(f"\nINVESTIGATING MISSING POST:")
print(f"  Title: {TARGET_POST_TITLE}")
print(f"  Date: {TARGET_POST_DATE}")
print(f"  Expected at: {TARGET_STAGING_URL}")
print(f"  Blog Category: {TARGET_BLOG_CATEGORY}")
print(f"  Keywords: {', '.join(TARGET_KEYWORDS)}")
print("="*80)

try:
    response = logs_client.filter_log_events(
        logGroupName='/ecs/selenium-crawler',
        startTime=start_time,
        limit=1000  # Increased limit for thorough investigation
    )
    
    if not response['events']:
        print("\nNo logs found in the last 6 hours")
        print("This means ECS tasks are NOT running!")
        print("\nACTION REQUIRED:")
        print("1. Check ECS task status in AWS Console")
        print("2. Verify EventBridge/CloudWatch Events schedule")
        print("3. Check ECS task role permissions")
        print("4. Review ECS task definition and container configuration")
        print("5. Check VPC/network connectivity for ECS tasks")
    else:
        print(f"\nFound {len(response['events'])} log events\n")
        
        # Categorize logs for investigation
        url_filtering_logs = []
        date_parsing_logs = []
        date_filtering_logs = []
        storage_logs = []
        workspaces_related_logs = []
        error_logs = []
        staging_url_logs = []
        blog_category_logs = []
        all_urls_found = []
        all_dates_parsed = []
        selenium_logs = []
        crawl_start_logs = []
        crawl_end_logs = []
        post_detection_logs = []
        domain_config_logs = []
        date_validation_logs = []
        
        # Print all logs and categorize
        for event in response['events']:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            print(f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {message}")
            
            # Categorize for investigation
            message_lower = message.lower()
            
            # Track crawler lifecycle
            if 'starting' in message_lower or 'initializing' in message_lower:
                crawl_start_logs.append((timestamp, message))
            if 'completed' in message_lower or 'finished' in message_lower or 'done' in message_lower:
                crawl_end_logs.append((timestamp, message))
            
            # Track domain configuration
            if 'domain' in message_lower or 'allowed' in message_lower or 'whitelist' in message_lower or 'config' in message_lower:
                domain_config_logs.append(message)
            
            # Track URLs being crawled
            if 'crawling' in message_lower or 'fetching' in message_lower or 'url:' in message_lower or 'visiting' in message_lower:
                all_urls_found.append(message)
                if TARGET_STAGING_URL in message_lower:
                    staging_url_logs.append(message)
                if TARGET_BLOG_CATEGORY in message_lower:
                    blog_category_logs.append(message)
            
            # Track URL filtering logic (why URLs might be skipped)
            if 'filter' in message_lower or 'skip' in message_lower or 'ignore' in message_lower or 'excluding' in message_lower or 'rejected' in message_lower:
                url_filtering_logs.append(message)
            
            # Track date parsing and filtering
            if 'date' in message_lower or 'parsing' in message_lower or '2026' in message or 'march' in message_lower:
                date_parsing_logs.append(message)
                # Extract dates if present
                date_match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}', message_lower)
                if date_match:
                    all_dates_parsed.append(date_match.group())
                
                # Check for date filtering logic
                if 'future' in message_lower or 'past' in message_lower or 'range' in message_lower or 'valid' in message_lower or 'invalid' in message_lower:
                    date_filtering_logs.append(message)
                    date_validation_logs.append(message)
            
            # Track post detection
            if 'post' in message_lower and ('found' in message_lower or 'detected' in message_lower or 'extracted' in message_lower):
                post_detection_logs.append(message)
            
            # Track storage operations
            if 'stor' in message_lower or 'save' in message_lower or 'write' in message_lower or 'dynamodb' in message_lower or 's3' in message_lower or 'persist' in message_lower:
                storage_logs.append(message)
            
            # Track WorkSpaces-related content
            if any(keyword in message_lower for keyword in TARGET_KEYWORDS):
                workspaces_related_logs.append(message)
            
            # Track blog category mentions
            if TARGET_BLOG_CATEGORY in message_lower:
                blog_category_logs.append(message)
            
            # Track Selenium-specific operations
            if 'selenium' in message_lower or 'webdriver' in message_lower or 'browser' in message_lower or 'chrome' in message_lower:
                selenium_logs.append(message)
            
            # Track errors
            if 'error' in message_lower or 'fatal' in message_lower or 'exception' in message_lower or 'fail' in message_lower or 'traceback' in message_lower:
                error_logs.append(message)
        
        # Investigation summary
        print("\n" + "="*80)
        print("INVESTIGATION SUMMARY:")
        print("="*80)
        
        messages = [e['message'] for e in response['events']]
        all_text = '\n'.join(messages)
        
        # 0. Crawler execution timeline
        print("\n0. CRAWLER EXECUTION TIMELINE:")
        if crawl_start_logs:
            print(f"   ✓ Crawler started {len(crawl_start_logs)} time(s):")
            for ts, log in crawl_start_logs[-3:]:  # Show last 3 starts
                print(f"      [{ts.strftime('%H:%M:%S')}] {log[:100]}...")
        else:
            print("   ✗ No crawler start logs found")
        
        if crawl_end_logs:
            print(f"   ✓ Crawler completed {len(crawl_end_logs)} time(s):")
            for ts, log in crawl_end_logs[-3:]:  # Show last 3 completions
                print(f"      [{ts.strftime('%H:%M:%S')}] {log[:100]}...")
        else:
            print("   ✗ No crawler completion logs found")
        
        # 1. Check crawler completion
        print("\n1. CRAWLER EXECUTION STATUS:")
        if 'posts updated - invoking summary generator' in all_text or 'summary generator' in all_text.lower():
            print("   ✓ Selenium crawler completed and invoked summary generator")
        else:
            print("   ✗ Selenium crawler did NOT complete properly or invoke summary generator")
        
        if 'Updated:' in all_text:
            count = all_text.count('Updated:')
            print(f"   ✓ Successfully updated {count} posts")
        else:
            print("   ✗ No posts were updated")
        
        if post_detection_logs:
            print(f"   ✓ Detected {len(post_detection_logs)} posts:")
            for log in post_detection_logs[:5]:
                print(f"      - {log[:120]}...")
        
        # 2. Domain configuration analysis
        print("\n2. DOMAIN CONFIGURATION ANALYSIS:")
        print(f"   Domain config logs: {len(domain_config_logs)}")
        
        if domain_config_logs:
            print("   Domain configuration mentions:")
            for log in domain_config_logs[:10]:
                print(f"      - {log[:120]}...")
            
            # Check if staging domain is in configuration
            staging_in_config = any(TARGET_STAGING_URL in log for log in domain_config_logs)
            if staging_in_config:
                print(f"   ✓ Staging domain ({TARGET_STAGING_URL}) found in configuration")
            else:
                print(f"   ✗ CRITICAL: Staging domain ({TARGET_STAGING_URL}) NOT found in configuration")
                print("   ROOT CAUSE: Crawler domain allowlist excludes staging environment")
        else:
            print("   ⚠ No domain configuration logs found")
        
        # 3. URL filtering investigation
        print("\n3. URL FILTERING ANALYSIS:")
        print(f"   Total URL-related logs: {len(all_urls_found)}")
        print(f"   Staging URL mentions: {len(staging_url_logs)}")
        print(f"   Blog category mentions: {len(blog_category_logs)}")
        print(f"   URLs filtered/skipped: {len(url_filtering_logs)}")
        
        if staging_url_logs:
            print(f"   ✓ Staging URL ({TARGET_STAGING_URL}) was accessed:")
            for log in staging_url_logs[:5]:  # Show first 5
                print(f"      - {log[:120]}...")
        else:
            print(f"   ✗ CRITICAL: No evidence of staging URL ({TARGET_STAGING_URL}) being crawled")
            print("   ISSUE: Crawler may not be configured to check staging domain")
            print("   ACTION: Verify crawler URL configuration includes staging domain")
        
        if blog_category_logs:
            print(f"   ✓ Blog category ({TARGET_BLOG_CATEGORY}) was accessed:")
            for log in blog_category_logs[:5]:
                print(f"      - {log[:120]}...")
        else:
            print(f"   ✗ CRITICAL: Blog category ({TARGET_BLOG_CATEGORY}) NOT accessed")
            print("   ISSUE: Crawler may not be crawling this specific blog category")
            print("   ACTION: Verify blog category URL patterns in crawler configuration")
        
        if url_filtering_logs:
            print(f"   ⚠ Found {len(url_filtering_logs)} filtered/skipped URLs:")
            for log in url_filtering_logs[:10]:  # Show first 10
                print(f"      - {log[:120]}...")
            # Check if WorkSpaces URLs are being filtered
            ws_filtered = [log for log in url_filtering_logs if any(kw in log.lower() for kw in TARGET_KEYWORDS)]
            if ws_filtered:
                print(f"   ✗ CRITICAL: {len(ws_filtered)} WorkSpaces-related URLs were filtered:")
                for log in ws_filtered:
                    print(f"      - {log[:120]}...")
            
            # Check if blog category URLs are being filtered
            category_filtered = [log for log in url_filtering_logs if TARGET_BLOG_CATEGORY in log.lower()]
            if category_filtered:
                print(f"   ✗ CRITICAL: {len(category_filtered)} blog category URLs were filtered:")
                for log in category_filtered:
                    print(f"      - {log[:120]}...")
        
        # 4. Date parsing investigation
        print("\n4. DATE PARSING ANALYSIS:")
        print(f"   Date-related logs: {len(date_parsing_logs)}")
        print(f"   Date filtering logs: {len(date_filtering_logs)}")
        print(f"   Date validation logs: {len(date_validation_logs)}")
        print(f"   Unique dates parsed: {len(set(all_dates_parsed))}")
        
        target_date_found = any(TARGET_POST_DATE.lower() in log.lower() or 'march 2, 2026' in log.lower() for log in date_parsing_logs)
        if target_date_found:
            print(f"   ✓ Target date ({TARGET_POST_DATE}) was parsed")
            matching_logs = [log for log in date_parsing_logs if TARGET_POST_DATE.lower() in log.lower() or 'march 2, 2026' in log.lower()]
            for log in matching_logs[:3]:
                print(f"      - {log[:120]}...")
        else:
            print(f"   ✗ CRITICAL: Target date ({TARGET_POST_DATE}) NOT found in parsing logs")
            print("   ISSUE: Date may be filtered out or parsed incorrectly")
        
        if all_dates_parsed:
            print(f"   Dates detected: {', '.join(list(set(all_dates_parsed))[:10])}")
        
        # Check for future date filtering (CRITICAL for March 2026)
        future_date_filtering = [log for log in date_validation_logs if 'future' in log.lower()]
        if future_date_filtering:
            print("   ✗ CRITICAL: Future date filtering detected!")
            print("   ROOT CAUSE: Crawler is filtering out March 2026 as future date")
            print("   RECOMMENDED FIX: Disable future date validation or adjust date range")
            for log in future_date_filtering[:5]:
                print(f"      - {log[:120]}...")
        
        # Check for date range restrictions
        date_range_logs = [log for log in date_validation_logs if 'range' in log.lower() or 'threshold' in log.lower()]
        if date_range_logs:
            print(f"   ⚠ Date range restrictions detected ({len(date_range_logs)} instances):")
            for log in date_range_logs[:5]:
                print(f"      - {log[:120]}...")
        
        if date_filtering_logs:
            print(f"   ⚠ Date filtering logic active ({len(date_filtering_logs)} instances):")
            for log in date_filtering_logs[:5]:
                print(f"      - {log[:120]}...")
        
        # 5. Storage mechanism investigation
        print("\n5. STORAGE MECHANISM ANALYSIS:")
        print(f"   Storage-related logs: {len(storage_logs)}")
        
        if storage_logs:
            print("   ✓ Storage operations detected:")
            for log in storage_logs[:10]:  # Show first 10
                print(f"      - {log[:120]}...")
        else:
            print("   ✗ No storage operations logged")
            print("   ISSUE: Posts may not be persisting to database/storage")
        
        # 6. WorkSpaces content detection
        print("\n6. TARGET POST DETECTION:")
        print(f"   WorkSpaces-related logs: {len(workspaces_related_logs)}")
        
        if workspaces_related_logs:
            print(f"   ✓ WorkSpaces content detected:")
            for log in workspaces_related_logs:
                print(f"