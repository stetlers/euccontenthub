import boto3
from datetime import datetime, timedelta

# Connect to CloudWatch Logs
logs_client = boto3.client('logs', region_name='us-east-1')
log_group = '/aws/lambda/aws-blog-summary-generator'

# Get logs from last 24 hours
start_time = int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)
end_time = int(datetime.now().timestamp() * 1000)

print(f"\n{'='*80}")
print(f"Summary Generator Lambda Logs - Auto-Chain Analysis")
print(f"{'='*80}\n")

try:
    # Search for auto-chain related log entries
    response = logs_client.filter_log_events(
        logGroupName=log_group,
        startTime=start_time,
        endTime=end_time,
        filterPattern='auto-chain'
    )
    
    if response['events']:
        print(f"Found {len(response['events'])} auto-chain related log entries:\n")
        for event in response['events'][-20:]:  # Show last 20
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            print(f"[{timestamp}] {event['message']}")
    else:
        print("No auto-chain log entries found in last 24 hours")
        
    # Also search for deployment marker
    print(f"\n{'='*80}")
    print("Checking for deployment marker...")
    print(f"{'='*80}\n")
    
    response = logs_client.filter_log_events(
        logGroupName=log_group,
        startTime=start_time,
        endTime=end_time,
        filterPattern='AUTOCHAIN-V2-DEPLOYED'
    )
    
    if response['events']:
        print(f"✓ Found deployment marker in {len(response['events'])} log entries")
        latest = response['events'][-1]
        timestamp = datetime.fromtimestamp(latest['timestamp'] / 1000)
        print(f"  Latest: [{timestamp}] {latest['message']}")
    else:
        print("✗ Deployment marker NOT found - old code may still be running")
        
    # Check for any errors
    print(f"\n{'='*80}")
    print("Checking for errors...")
    print(f"{'='*80}\n")
    
    response = logs_client.filter_log_events(
        logGroupName=log_group,
        startTime=start_time,
        endTime=end_time,
        filterPattern='ERROR'
    )
    
    if response['events']:
        print(f"Found {len(response['events'])} error entries (showing last 5):\n")
        for event in response['events'][-5:]:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            print(f"[{timestamp}] {event['message']}\n")
    else:
        print("No errors found")
        
except Exception as e:
    print(f"Error checking logs: {e}")
