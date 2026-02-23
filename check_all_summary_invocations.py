import boto3
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')
log_group = '/aws/lambda/aws-blog-summary-generator'

# Get logs from last 15 minutes
start_time = int((datetime.now() - timedelta(minutes=15)).timestamp() * 1000)
end_time = int(datetime.now().timestamp() * 1000)

print(f"\n{'='*80}")
print(f"All Summary Generator Invocations (last 15 minutes)")
print(f"{'='*80}\n")

try:
    # Search for START messages (one per invocation)
    response = logs_client.filter_log_events(
        logGroupName=log_group,
        startTime=start_time,
        endTime=end_time,
        filterPattern='START RequestId'
    )
    
    if response['events']:
        print(f"Found {len(response['events'])} Lambda invocations:\n")
        for i, event in enumerate(response['events'], 1):
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            print(f"{i}. [{timestamp.strftime('%H:%M:%S')}] {message}")
    else:
        print("No invocations found")
        
except Exception as e:
    print(f"Error: {e}")
