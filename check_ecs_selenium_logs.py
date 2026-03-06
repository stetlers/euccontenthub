```python
import boto3
from datetime import datetime, timedelta
import json
import re

logs_client = boto3.client('logs', region_name='us-east-1')

print("="*80)
print("CHECKING ECS SELENIUM CRAWLER LOGS - INVESTIGATION MODE")
print("="*80)

# Get logs from the last 3 hours
start_time = int((datetime.now() - timedelta(hours=3)).timestamp() * 1000)

# Target blog post details for investigation
TARGET_POST_TITLE = "Amazon WorkSpaces launches Graphics G6, Gr6, and G6f bundles"
TARGET_POST_DATE = "March 2, 2026"
TARGET_STAGING_URL = "staging.awseuccontent.com"

print(f"\nINVESTIGATING MISSING POST:")
print(f"  Title: {TARGET_POST_TITLE}")
print(f"  Date: {TARGET_POST_DATE}")
print(f"  Expected at: {TARGET_STAGING_URL}")
print("="*80)

try:
    response = logs_client.filter_log_events(
        logGroupName='/ecs/selenium-crawler',
        startTime=start_time,
        limit=500  # Increased limit for thorough investigation
    )
    
    if not response['events']:
        print("\nNo logs found in the last 3 hours")
        print("This means ECS tasks are NOT running!")
        print("\nACTION REQUIRED:")
        print("1. Check ECS task status in AWS Console")
        print("2. Verify EventBridge/CloudWatch Events schedule")
        print("3. Check ECS task role permissions")
    else:
        print(f"\nFound {len(response['events'])} log events\n")
        
        # Categorize logs for investigation
        url_filtering_logs = []
        date_parsing_logs = []
        storage_logs = []
        workspaces_related_logs = []
        error_logs = []
        staging_url_logs = []
        all_urls_found = []
        all_dates_parsed = []
        
        # Print all logs and categorize
        for event in response['events']:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
            
            # Categorize for investigation
            message_lower = message.lower()
            
            # Track URLs being crawled
            if 'crawling' in message_lower or 'fetching' in message_lower or 'url:' in message_lower:
                all_urls_found.append(message)
                if TARGET_STAGING_URL in message_lower:
                    staging_url_logs.append(message)
            
            # Track URL filtering logic
            if 'filter' in message_lower or 'skip' in message_lower or 'ignore' in message_lower:
                url_filtering_logs.append(message)
            
            # Track date parsing
            if 'date' in message_lower or 'parsing' in message_lower or '2026' in message:
                date_parsing_logs.append(message)
                # Extract dates if present
                date_match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},\s+\d{4}', message_lower)
                if date_match:
                    all_dates_parsed.append(date_match.group())
            
            # Track storage operations
            if 'stor' in message_lower or 'save' in message_lower or 'write' in message_lower or 'dynamodb' in message_lower or 's3' in message_lower:
                storage_logs.append(message)
            
            # Track WorkSpaces-related content
            if 'workspaces' in message_lower or 'g6' in message_lower or 'gr6' in message_lower or 'graphics' in message_lower:
                workspaces_related_logs.append(message)
            
            # Track errors
            if 'error' in message_lower or 'fatal' in message_lower or 'exception' in message_lower or 'fail' in message_lower:
                error_logs.append(message)
        
        # Investigation summary
        print("\n" + "="*80)
        print("INVESTIGATION SUMMARY:")
        print("="*80)
        
        messages = [e['message'] for e in response['events']]
        all_text = '\n'.join(messages)
        
        # 1. Check crawler completion
        print("\n1. CRAWLER EXECUTION STATUS:")
        if 'posts updated - invoking summary generator' in all_text:
            print("   ✓ Selenium crawler completed and invoked summary generator")
        else:
            print("   ✗ Selenium crawler did NOT complete properly")
        
        if 'Updated:' in all_text:
            count = all_text.count('Updated:')
            print(f"   ✓ Successfully updated {count} posts")
        else:
            print("   ✗ No posts were updated")
        
        # 2. URL filtering investigation
        print("\n2. URL FILTERING ANALYSIS:")
        print(f"   Total URL-related logs: {len(all_urls_found)}")
        print(f"   Staging URL mentions: {len(staging_url_logs)}")
        print(f"   URLs filtered/skipped: {len(url_filtering_logs)}")
        
        if staging_url_logs:
            print(f"   ✓ Staging URL ({TARGET_STAGING_URL}) was accessed")
            for log in staging_url_logs[:5]:  # Show first 5
                print(f"      - {log[:120]}...")
        else:
            print(f"   ✗ No evidence of staging URL ({TARGET_STAGING_URL}) being crawled")
            print("   ISSUE: Crawler may not be configured to check staging domain")
        
        if url_filtering_logs:
            print(f"   ⚠ Found {len(url_filtering_logs)} filtered/skipped URLs:")
            for log in url_filtering_logs[:5]:  # Show first 5
                print(f"      - {log[:120]}...")
        
        # 3. Date parsing investigation
        print("\n3. DATE PARSING ANALYSIS:")
        print(f"   Date-related logs: {len(date_parsing_logs)}")
        print(f"   Unique dates parsed: {len(set(all_dates_parsed))}")
        
        target_date_found = any(TARGET_POST_DATE.lower() in log.lower() for log in date_parsing_logs)
        if target_date_found:
            print(f"   ✓ Target date ({TARGET_POST_DATE}) was parsed")
        else:
            print(f"   ✗ Target date ({TARGET_POST_DATE}) NOT found in parsing logs")
            print("   ISSUE: Date may be filtered out or parsed incorrectly")
        
        if all_dates_parsed:
            print(f"   Dates detected: {', '.join(set(all_dates_parsed)[:10])}")
        
        # Check for future date filtering
        if any('future' in log.lower() for log in date_parsing_logs):
            print("   ⚠ CRITICAL: Future date filtering detected!")
            print("   LIKELY ROOT CAUSE: Crawler may be filtering out March 2026 as future date")
        
        # 4. Storage mechanism investigation
        print("\n4. STORAGE MECHANISM ANALYSIS:")
        print(f"   Storage-related logs: {len(storage_logs)}")
        
        if storage_logs:
            print("   Storage operations detected:")
            for log in storage_logs[:5]:  # Show first 5
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
        else:
            print("   ✗ No WorkSpaces-related content detected")
            print("   ISSUE: Post may not be visible to crawler or filtered out")
        
        # 6. Error analysis
        print("\n6. ERROR ANALYSIS:")
        if error_logs:
            print(f"   ✗ Found {len(error_logs)} errors:")
            for log in error_logs[:10]:  # Show first 10 errors
                print(f"      - {log[:120]}...")
        else:
            print("   ✓ No errors detected in logs")
        
        # 7. Root cause hypothesis
        print("\n" + "="*80)
        print("ROOT CAUSE HYPOTHESIS:")
        print("="*80)
        
        hypotheses = []
        
        if not staging_url_logs:
            hypotheses.append("1. Crawler not configured to check staging.awseuccontent.com domain")
        
        if 'future' in all_text.lower():
            hypotheses.append("2. Date filter rejecting March 2026 as future date (MOST LIKELY)")
        
        if not workspaces_related_logs and staging_url_logs:
            hypotheses.append("3. Post exists but title/content filtering is excluding it")
        
        if error_logs:
            hypotheses.append("4. Errors preventing proper crawling or storage")
        
        if not storage_logs:
            hypotheses.append("5. Storage mechanism failing to persist data")
        
        if url_filtering_logs and 'workspaces' in ' '.join(url_filtering_logs).lower():
            hypotheses.append("6. URL pattern matching incorrectly filtering WorkSpaces URLs")
        
        if not hypotheses:
            hypotheses.append("1. Post may not be published yet on staging environment")
            hypotheses.append("2. Selenium rendering issue preventing content detection")
            hypotheses.append("3. Post metadata (title, date) not matching expected format")
        
        for hypothesis in hypotheses:
            print(f"   {hypothesis}")
        
        # 8. Recommended actions
        print("\n" + "="*80)
        print("RECOMMENDED ACTIONS:")
        print("="*80)
        print("   1. Check crawler configuration for staging URL allowlist")
        print("   2. Review date filtering logic - disable future date rejection if present")
        print("   3. Verify post is actually published at staging.awseuccontent.com")
        print("   4. Test date parser with 'March 2, 2026' format")
        print("   5. Review URL filtering patterns for 'workspaces' keyword")
        print("   6. Check DynamoDB/storage for partial data with WorkSpaces content")
        print("   7. Run crawler with debug logging enabled")
        print("   8. Manually verify post accessibility with Selenium headless browser")
        
except Exception as e:
    print(f"ERROR: {e}")
    print("\nPossible causes:")
    print("1. Log group doesn't exist")
    print("2. No ECS tasks have run recently")
    print("3. AWS credentials expired")
    print("4. Insufficient permissions to read logs")
```