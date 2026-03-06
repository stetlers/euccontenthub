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
TARGET_KEYWORDS = ["workspaces", "g6", "gr6", "g6f", "graphics"]

print(f"\nINVESTIGATING MISSING POST:")
print(f"  Title: {TARGET_POST_TITLE}")
print(f"  Date: {TARGET_POST_DATE}")
print(f"  Expected at: {TARGET_STAGING_URL}")
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
        all_urls_found = []
        all_dates_parsed = []
        selenium_logs = []
        crawl_start_logs = []
        crawl_end_logs = []
        post_detection_logs = []
        
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
            
            # Track URLs being crawled
            if 'crawling' in message_lower or 'fetching' in message_lower or 'url:' in message_lower or 'visiting' in message_lower:
                all_urls_found.append(message)
                if TARGET_STAGING_URL in message_lower:
                    staging_url_logs.append(message)
            
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
                if 'future' in message_lower or 'past' in message_lower or 'range' in message_lower:
                    date_filtering_logs.append(message)
            
            # Track post detection
            if 'post' in message_lower and ('found' in message_lower or 'detected' in message_lower or 'extracted' in message_lower):
                post_detection_logs.append(message)
            
            # Track storage operations
            if 'stor' in message_lower or 'save' in message_lower or 'write' in message_lower or 'dynamodb' in message_lower or 's3' in message_lower or 'persist' in message_lower:
                storage_logs.append(message)
            
            # Track WorkSpaces-related content
            if any(keyword in message_lower for keyword in TARGET_KEYWORDS):
                workspaces_related_logs.append(message)
            
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
        
        # 2. URL filtering investigation
        print("\n2. URL FILTERING ANALYSIS:")
        print(f"   Total URL-related logs: {len(all_urls_found)}")
        print(f"   Staging URL mentions: {len(staging_url_logs)}")
        print(f"   URLs filtered/skipped: {len(url_filtering_logs)}")
        
        if staging_url_logs:
            print(f"   ✓ Staging URL ({TARGET_STAGING_URL}) was accessed:")
            for log in staging_url_logs[:5]:  # Show first 5
                print(f"      - {log[:120]}...")
        else:
            print(f"   ✗ CRITICAL: No evidence of staging URL ({TARGET_STAGING_URL}) being crawled")
            print("   ISSUE: Crawler may not be configured to check staging domain")
            print("   ACTION: Verify crawler URL configuration includes staging domain")
        
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
        
        # 3. Date parsing investigation
        print("\n3. DATE PARSING ANALYSIS:")
        print(f"   Date-related logs: {len(date_parsing_logs)}")
        print(f"   Date filtering logs: {len(date_filtering_logs)}")
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
        if any('future' in log.lower() for log in date_parsing_logs):
            print("   ✗ CRITICAL: Future date filtering detected!")
            print("   ROOT CAUSE: Crawler is filtering out March 2026 as future date")
            future_logs = [log for log in date_parsing_logs if 'future' in log.lower()]
            for log in future_logs[:5]:
                print(f"      - {log[:120]}...")
        
        if date_filtering_logs:
            print(f"   ⚠ Date filtering logic active ({len(date_filtering_logs)} instances):")
            for log in date_filtering_logs[:5]:
                print(f"      - {log[:120]}...")
        
        # 4. Storage mechanism investigation
        print("\n4. STORAGE MECHANISM ANALYSIS:")
        print(f"   Storage-related logs: {len(storage_logs)}")
        
        if storage_logs:
            print("   ✓ Storage operations detected:")
            for log in storage_logs[:10]:  # Show first 10
                print(f"      - {log[:120]}...")
        else:
            print("   ✗ No storage operations logged")
            print("   ISSUE: Posts may not be persisting to database/storage")
        
        # 5. WorkSpaces content detection
        print("\n5. TARGET POST DETECTION:")
        print(f"   WorkSpaces-related logs: {len(workspaces_related_logs)}")
        
        if workspaces_related_logs:
            print(f"   ✓ WorkSpaces content detected:")
            for log in workspaces_related_logs:
                print(f"      - {log[:120]}...")
            
            # Check if title matches
            title_match = any(TARGET_POST_TITLE.lower() in log.lower() for log in workspaces_related_logs)
            if title_match:
                print(f"   ✓ Exact title match found!")
            else:
                print(f"   ⚠ WorkSpaces content found but not exact title match")
        else:
            print("   ✗ CRITICAL: No WorkSpaces-related content detected")
            print("   ISSUE: Post may not be visible to crawler, filtered out, or not yet published")
        
        # 6. Selenium/browser investigation
        print("\n6. SELENIUM/BROWSER ANALYSIS:")
        if selenium_logs:
            print(f"   ✓ Selenium operations detected ({len(selenium_logs)} logs):")
            for log in selenium_logs[:5]:
                print(f"      - {log[:120]}...")
        else:
            print("   ⚠ No explicit Selenium logs found")
        
        # 7. Error analysis
        print("\n7. ERROR ANALYSIS:")
        if error_logs:
            print(f"   ✗ Found {len(error_logs)} errors:")
            for log in error_logs[:15]:  # Show first 15 errors
                print(f"      - {log[:150]}...")
        else:
            print("   ✓ No errors detected in logs")
        
        # 8. Root cause hypothesis
        print("\n" + "="*80)
        print("ROOT CAUSE HYPOTHESIS (PRIORITY ORDER):")
        print("="*80)
        
        hypotheses = []
        
        # Priority 1: Date filtering
        if any('future' in log.lower() for log in date_parsing_logs):
            hypotheses.append("1. [HIGH CONFIDENCE] Date filter rejecting March 2026 as future date")
            hypotheses.append("   - Crawler likely has future date validation logic")
            hypotheses.append("   - March 2, 2026 exceeds current date threshold")
        
        # Priority 2: Staging URL not configured
        if not staging_url_logs and len(all_urls_found) > 0:
            hypotheses.append("2. [HIGH CONFIDENCE] Crawler not configured to check staging.awseuccontent.com")
            hypotheses.append("   - Crawler is running but not accessing staging environment")
            hypotheses.append("   - URL allowlist may only include production domains")
        
        # Priority 3: Post filtering
        if url_filtering_logs and any(kw in ' '.join(url_filtering_logs).lower() for kw in TARGET_KEYWORDS):
            hypotheses.append("3. [MEDIUM CONFIDENCE] URL pattern filtering excluding WorkSpaces URLs")
            hypotheses.append("   - WorkSpaces keywords detected in filtering logs")
        
        # Priority 4: Post not detected
        if staging_url_logs and not workspaces_related_logs:
            hypotheses.append("4. [MEDIUM CONFIDENCE] Post exists but content not detected by crawler")
            hypotheses.append("   - Staging accessed but WorkSpaces content not found")
            hypotheses.append("   - May be Selenium rendering issue or element selector problem")
        
        # Priority 5: Storage failure
        if workspaces_related_logs and not storage_logs:
            hypotheses.append("5. [MEDIUM CONFIDENCE] Post detected but storage mechanism failing")
            hypotheses.append("   - Content found but not persisted to database")
        
        