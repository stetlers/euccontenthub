```python
import boto3
from datetime import datetime, timedelta
import re

logs_client = boto3.client('logs', region_name='us-east-1')
dynamodb = boto3.client('dynamodb', region_name='us-east-1')

print("="*80)
print("CHECKING ECS SELENIUM CRAWLER LOGS")
print("="*80)

# Get logs from the last 3 hours
start_time = int((datetime.now() - timedelta(hours=3)).timestamp() * 1000)

# Target blog post to investigate
TARGET_POST_DATE = "March 2, 2026"
TARGET_POST_KEYWORDS = ["Amazon WorkSpaces Graphics", "WorkSpaces Graphics bundles"]

try:
    response = logs_client.filter_log_events(
        logGroupName='/ecs/selenium-crawler',
        startTime=start_time,
        limit=100
    )
    
    if not response['events']:
        print("\nNo logs found in the last 3 hours")
        print("This means ECS tasks are NOT running!")
    else:
        print(f"\nFound {len(response['events'])} log events\n")
        
        # Print all logs
        for event in response['events']:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
        
        # Look for key indicators
        print("\n" + "="*80)
        print("KEY INDICATORS:")
        print("="*80)
        
        messages = [e['message'] for e in response['events']]
        all_text = '\n'.join(messages)
        
        if 'posts updated - invoking summary generator' in all_text:
            print("✓ Selenium crawler completed and invoked summary generator")
        else:
            print("✗ Selenium crawler did NOT invoke summary generator")
        
        if 'Updated:' in all_text:
            count = all_text.count('Updated:')
            print(f"✓ Successfully updated {count} posts")
        else:
            print("✗ No posts were updated")
        
        if 'ERROR' in all_text or 'FATAL' in all_text:
            print("✗ Errors detected in logs")
        
        # Investigation for missing blog post
        print("\n" + "="*80)
        print(f"INVESTIGATING MISSING POST: {TARGET_POST_DATE}")
        print("="*80)
        
        # Check if the target post was detected
        target_post_found = False
        for keyword in TARGET_POST_KEYWORDS:
            if keyword.lower() in all_text.lower():
                target_post_found = True
                print(f"✓ Found reference to '{keyword}' in crawler logs")
                break
        
        if not target_post_found:
            print(f"✗ No reference to target post from {TARGET_POST_DATE} found")
        
        # Check for date-related filtering
        if TARGET_POST_DATE in all_text or "March 2" in all_text or "2026-03-02" in all_text:
            print(f"✓ Date reference found in logs")
        else:
            print(f"✗ No date reference found for {TARGET_POST_DATE}")
        
        # Check for filtering logic issues
        if 'filtered' in all_text.lower() or 'skipped' in all_text.lower():
            print("⚠ Found filtering/skipping activity - examining...")
            for msg in messages:
                if 'filtered' in msg.lower() or 'skipped' in msg.lower():
                    print(f"  - {msg}")
        
        # Check for DynamoDB write operations
        if 'dynamodb' in all_text.lower() or 'writing' in all_text.lower() or 'storing' in all_text.lower():
            print("✓ Found DynamoDB write operations in logs")
        else:
            print("⚠ No explicit DynamoDB write operations found in logs")
        
        # Count total posts processed
        processed_count = len(re.findall(r'Processing post:|Crawled post:|Found post:', all_text, re.IGNORECASE))
        if processed_count > 0:
            print(f"✓ Processed {processed_count} posts total")
        
        # Check for URL accessibility issues
        if '404' in all_text or 'not found' in all_text.lower() or 'unreachable' in all_text.lower():
            print("✗ Found accessibility issues (404/not found)")
        
        # Check for Selenium errors
        if 'selenium' in all_text.lower() and 'error' in all_text.lower():
            print("✗ Selenium errors detected")
        
        # Verify staging environment
        if 'staging' in all_text.lower():
            print("✓ Confirmed running in staging environment")
        elif 'production' in all_text.lower() or 'prod' in all_text.lower():
            print("⚠ WARNING: Logs may be from production, not staging!")
        
except logs_client.exceptions.ResourceNotFoundException:
    print("ERROR: Log group '/ecs/selenium-crawler' does not exist")
    print("\nPossible causes:")
    print("1. Log group name is incorrect")
    print("2. ECS tasks have never run")
    print("3. Wrong AWS region")
except Exception as e:
    print(f"ERROR: {e}")
    print("\nPossible causes:")
    print("1. Log group doesn't exist")
    print("2. No ECS tasks have run recently")
    print("3. AWS credentials expired")

# Additional check: Verify DynamoDB table for the post
print("\n" + "="*80)
print("CHECKING DYNAMODB FOR TARGET POST")
print("="*80)

try:
    # Scan DynamoDB for posts from target date
    table_name = 'aws-whats-new-staging'
    
    scan_response = dynamodb.scan(
        TableName=table_name,
        FilterExpression='contains(#date, :target_date) OR contains(title, :workspaces)',
        ExpressionAttributeNames={
            '#date': 'date'
        },
        ExpressionAttributeValues={
            ':target_date': {'S': TARGET_POST_DATE},
            ':workspaces': {'S': 'WorkSpaces Graphics'}
        },
        Limit=50
    )
    
    if scan_response['Items']:
        print(f"✓ Found {len(scan_response['Items'])} matching posts in DynamoDB:")
        for item in scan_response['Items']:
            title = item.get('title', {}).get('S', 'N/A')
            date = item.get('date', {}).get('S', 'N/A')
            print(f"  - [{date}] {title}")
    else:
        print(f"✗ No posts matching '{TARGET_POST_DATE}' or 'WorkSpaces Graphics' found in DynamoDB")
        print("  This confirms the post was NOT written to the database")
        
except dynamodb.exceptions.ResourceNotFoundException:
    print(f"ERROR: DynamoDB table '{table_name}' not found")
except Exception as e:
    print(f"ERROR checking DynamoDB: {e}")

print("\n" + "="*80)
print("DIAGNOSIS SUMMARY")
print("="*80)
print("Next steps:")
print("1. Check if blog post URL is accessible in staging environment")
print("2. Review crawler filtering logic for date/content matching")
print("3. Verify DynamoDB permissions and write operations")
print("4. Check if crawler is using correct date parsing logic")
print("5. Examine crawler configuration for post detection criteria")
print("="*80)
```