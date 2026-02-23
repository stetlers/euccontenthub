import boto3
from datetime import datetime

logs_client = boto3.client('logs', region_name='us-east-1')

print("=" * 60)
print("Full Selenium Crawler Logs")
print("=" * 60)

log_group = '/aws/lambda/aws-blog-builder-selenium-crawler'

try:
    # Get most recent log stream
    streams_response = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=1
    )
    
    if streams_response['logStreams']:
        stream = streams_response['logStreams'][0]
        print(f"\nLog stream: {stream['logStreamName']}")
        print(f"Last event: {datetime.fromtimestamp(stream['lastEventTimestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get ALL events from this stream
        events_response = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream['logStreamName'],
            startFromHead=True  # Start from beginning
        )
        
        print(f"\nTotal events: {len(events_response['events'])}")
        print("\nSearching for test post and key events...")
        print("-" * 60)
        
        # Look for key events
        for event in events_response['events']:
            message = event['message'].strip()
            
            # Look for our test post
            if 'building-a-simple-content-summarizer' in message.lower():
                print(f"\n>>> TEST POST: {message}")
            
            # Look for START/END
            elif 'START RequestId' in message:
                print(f"\n{message}")
            elif 'END RequestId' in message or 'REPORT RequestId' in message:
                print(f"{message}")
            
            # Look for post_ids parameter
            elif 'post_ids' in message.lower():
                print(f"\n>>> POST_IDS: {message}")
            
            # Look for summary invocation
            elif 'summary' in message.lower() and 'invok' in message.lower():
                print(f"\n>>> SUMMARY: {message}")
            
            # Look for errors
            elif 'error' in message.lower() or 'failed' in message.lower():
                print(f"\n⚠ ERROR: {message[:150]}")
        
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
