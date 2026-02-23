"""
Check summary generator logs from yesterday
"""
import boto3
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')

log_group = '/aws/lambda/aws-blog-summary-generator'

print("Checking Summary Generator Logs...")
print("=" * 80)

try:
    # Get log streams from the last 24 hours
    start_time = int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)
    
    streams = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=10
    )
    
    if streams['logStreams']:
        print(f"Found {len(streams['logStreams'])} recent log streams\n")
        
        # Check the most recent stream
        stream_name = streams['logStreams'][0]['logStreamName']
        last_event_time = streams['logStreams'][0].get('lastEventTime', 0)
        last_event_dt = datetime.fromtimestamp(last_event_time / 1000)
        
        print(f"Most recent stream: {stream_name}")
        print(f"Last event: {last_event_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Get recent events
        events = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            startFromHead=False,
            limit=50
        )
        
        if events['events']:
            print("Recent log messages:")
            print("-" * 80)
            for event in events['events'][-30:]:
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                print(f"[{timestamp.strftime('%H:%M:%S')}] {event['message'].strip()}")
        else:
            print("No log events found in this stream")
            
        # Check if there were any errors
        print("\n" + "=" * 80)
        print("Checking for errors across all recent streams...")
        print("-" * 80)
        
        error_count = 0
        for stream in streams['logStreams'][:5]:
            try:
                events = logs_client.get_log_events(
                    logGroupName=log_group,
                    logStreamName=stream['logStreamName'],
                    startFromHead=False,
                    limit=100
                )
                
                for event in events['events']:
                    msg = event['message']
                    if any(keyword in msg.lower() for keyword in ['error', 'exception', 'failed', 'traceback']):
                        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                        print(f"[{timestamp.strftime('%H:%M:%S')}] {msg.strip()}")
                        error_count += 1
            except:
                pass
        
        if error_count == 0:
            print("No errors found in recent logs")
    else:
        print("No log streams found")

except Exception as e:
    print(f"Error: {e}")
