import boto3
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')

log_group = '/ecs/selenium-crawler'
task_id = '379d1cf8aae4412391b78fa0ef9717a4'

print(f"Fetching logs for task: {task_id}")
print("=" * 80)

# Get log streams for this task
response = logs_client.describe_log_streams(
    logGroupName=log_group,
    logStreamNamePrefix=f'ecs/selenium-crawler/{task_id}',
    descending=True,
    limit=5
)

if not response['logStreams']:
    print("No log streams found. Trying broader search...")
    # Try without task ID prefix
    response = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=5
    )

if response['logStreams']:
    log_stream = response['logStreams'][0]['logStreamName']
    print(f"Log stream: {log_stream}\n")
    
    # Get log events
    events_response = logs_client.get_log_events(
        logGroupName=log_group,
        logStreamName=log_stream,
        startFromHead=True
    )
    
    if events_response['events']:
        print("Log output:")
        print("-" * 80)
        for event in events_response['events']:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            print(f"[{timestamp}] {event['message']}")
    else:
        print("No log events found")
else:
    print("No log streams found for this task")
    print("\nAvailable log streams:")
    all_streams = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=10
    )
    for stream in all_streams['logStreams']:
        print(f"  - {stream['logStreamName']}")
