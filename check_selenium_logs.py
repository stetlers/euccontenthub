import boto3
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')

print("=" * 60)
print("Selenium Crawler Logs")
print("=" * 60)

log_group = '/aws/lambda/aws-blog-builder-selenium-crawler'

try:
    # Get log streams
    streams_response = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=3
    )
    
    print(f"\nRecent log streams:")
    for stream in streams_response['logStreams']:
        last_event = datetime.fromtimestamp(stream['lastEventTimestamp'] / 1000)
        print(f"  - {stream['logStreamName']}")
        print(f"    Last event: {last_event.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get logs from most recent stream
    if streams_response['logStreams']:
        most_recent_stream = streams_response['logStreams'][0]['logStreamName']
        print(f"\nFetching logs from: {most_recent_stream}")
        
        events_response = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=most_recent_stream,
            limit=100,
            startFromHead=False
        )
        
        print(f"\nLast 50 log lines:")
        print("-" * 60)
        for event in events_response['events'][-50:]:
            message = event['message'].strip()
            if message:
                print(message)
        
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
