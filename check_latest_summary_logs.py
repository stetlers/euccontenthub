import boto3
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')
log_group = '/aws/lambda/aws-blog-summary-generator'

# Get logs from last 10 minutes only
start_time = int((datetime.now() - timedelta(minutes=10)).timestamp() * 1000)
end_time = int(datetime.now().timestamp() * 1000)

print(f"\n{'='*80}")
print(f"Latest Summary Generator Logs (last 10 minutes)")
print(f"{'='*80}\n")

try:
    # Get all recent log events
    response = logs_client.filter_log_events(
        logGroupName=log_group,
        startTime=start_time,
        endTime=end_time
    )
    
    if response['events']:
        print(f"Found {len(response['events'])} log entries:\n")
        for event in response['events']:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
    else:
        print("No log entries found in last 10 minutes")
        print("\nThis could mean:")
        print("  1. Lambda hasn't been invoked yet")
        print("  2. Lambda is still cold-starting")
        print("  3. Logs haven't propagated yet (can take 30-60 seconds)")
        
except Exception as e:
    print(f"Error: {e}")
