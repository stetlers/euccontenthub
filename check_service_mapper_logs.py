"""Check CloudWatch logs for service mapper initialization"""
import boto3
from datetime import datetime, timedelta

# Initialize CloudWatch Logs client
logs_client = boto3.client('logs', region_name='us-east-1')

# Lambda function name
FUNCTION_NAME = 'aws-blog-chat-assistant'
LOG_GROUP = f'/aws/lambda/{FUNCTION_NAME}'

print("Checking CloudWatch logs for service mapper initialization...")
print("=" * 70)

try:
    # Get recent log streams (last 5 minutes)
    response = logs_client.describe_log_streams(
        logGroupName=LOG_GROUP,
        orderBy='LastEventTime',
        descending=True,
        limit=5
    )
    
    if not response['logStreams']:
        print("No recent log streams found")
        exit(0)
    
    # Check the most recent log stream
    latest_stream = response['logStreams'][0]
    stream_name = latest_stream['logStreamName']
    
    print(f"Latest log stream: {stream_name}")
    print(f"Last event: {datetime.fromtimestamp(latest_stream['lastEventTimestamp']/1000)}")
    print()
    
    # Get log events
    events_response = logs_client.get_log_events(
        logGroupName=LOG_GROUP,
        logStreamName=stream_name,
        limit=100,
        startFromHead=False  # Get most recent events
    )
    
    # Filter for service mapper related messages
    mapper_logs = []
    for event in events_response['events']:
        message = event['message']
        if any(keyword in message for keyword in ['service mapper', 'Service mapper', 'EUCServiceMapper', 'service mapping']):
            mapper_logs.append(message)
    
    if mapper_logs:
        print("Service Mapper Initialization Logs:")
        print("-" * 70)
        for log in mapper_logs:
            print(log.strip())
        print()
        
        # Check for success
        if any('initialized successfully' in log for log in mapper_logs):
            print("✓ Service mapper initialized successfully!")
        elif any('ERROR' in log for log in mapper_logs):
            print("✗ Service mapper initialization failed")
        else:
            print("⚠ Service mapper status unclear")
    else:
        print("No service mapper logs found in recent events")
        print("\nShowing last 10 log messages:")
        print("-" * 70)
        for event in events_response['events'][-10:]:
            print(event['message'].strip())

except Exception as e:
    print(f"Error checking logs: {e}")
    import traceback
    traceback.print_exc()
