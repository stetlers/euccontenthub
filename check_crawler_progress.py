"""
Check crawler progress in real-time
"""
import boto3
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')

log_group = '/aws/lambda/aws-blog-crawler'

print("Fetching latest crawler logs...")
print("=" * 80)

try:
    # Get the most recent log stream
    streams = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=1
    )
    
    if streams['logStreams']:
        stream_name = streams['logStreams'][0]['logStreamName']
        last_event_time = streams['logStreams'][0].get('lastEventTime', 0)
        last_event_dt = datetime.fromtimestamp(last_event_time / 1000)
        
        print(f"Log stream: {stream_name}")
        print(f"Last event: {last_event_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Get recent events (last 100)
        events = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            startFromHead=False,
            limit=100
        )
        
        print("Recent log messages:")
        print("-" * 80)
        
        for event in events['events'][-30:]:  # Last 30 messages
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
    
    else:
        print("No log streams found")

except Exception as e:
    print(f"Error: {e}")
