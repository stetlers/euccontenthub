"""
Check summary generator Lambda logs with more detail
"""
import boto3
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')

log_group = '/aws/lambda/aws-blog-summary-generator'

print("=" * 80)
print("CHECKING SUMMARY GENERATOR LOGS (last 2 hours)")
print("=" * 80)

try:
    # Get recent log streams
    response = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=10
    )
    
    if not response['logStreams']:
        print("\n❌ No recent log streams found")
        exit(0)
    
    print(f"\nFound {len(response['logStreams'])} recent log streams")
    
    # Show all recent streams with timestamps
    print("\nRecent invocations:")
    for stream in response['logStreams'][:10]:
        stream_name = stream['logStreamName']
        last_event = datetime.fromtimestamp(stream['lastEventTimestamp'] / 1000)
        print(f"  {last_event.strftime('%Y-%m-%d %H:%M:%S')} - {stream_name}")
    
    # Get logs from the most recent stream
    latest_stream = response['logStreams'][0]
    stream_name = latest_stream['logStreamName']
    last_event = datetime.fromtimestamp(latest_stream['lastEventTimestamp'] / 1000)
    
    print(f"\n" + "=" * 80)
    print(f"Latest stream: {stream_name}")
    print(f"Last event: {last_event.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)
    
    # Get log events (last 100 lines)
    log_response = logs_client.get_log_events(
        logGroupName=log_group,
        logStreamName=stream_name,
        limit=100,
        startFromHead=False
    )
    
    for event in log_response['events']:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event['message'].strip()
        print(f"{timestamp.strftime('%H:%M:%S')} | {message}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
