import boto3
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')

print("="*80)
print("CHECKING ECS SELENIUM CRAWLER LOGS")
print("="*80)

# Get logs from the last 3 hours
start_time = int((datetime.now() - timedelta(hours=3)).timestamp() * 1000)

try:
    response = logs_client.filter_log_events(
        logGroupName='/ecs/selenium-crawler',
        startTime=start_time,
        limit=100
    )
    
    if not response['events']:
        print("\nNo logs found in the last hour")
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
        
except Exception as e:
    print(f"ERROR: {e}")
    print("\nPossible causes:")
    print("1. Log group doesn't exist")
    print("2. No ECS tasks have run recently")
    print("3. AWS credentials expired")
