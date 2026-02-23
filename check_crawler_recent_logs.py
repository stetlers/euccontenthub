"""
Check recent crawler Lambda logs to see if it ran
"""
import boto3
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')

log_group = '/aws/lambda/aws-blog-crawler'

print("=" * 80)
print("CHECKING RECENT CRAWLER LOGS (last 2 hours)")
print("=" * 80)

# Get log streams from the last 2 hours
end_time = datetime.utcnow()
start_time = end_time - timedelta(hours=2)

try:
    # Get recent log streams
    response = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=5
    )
    
    if not response['logStreams']:
        print("\n❌ No recent log streams found")
        print("   The crawler may not have been invoked yet")
        exit(0)
    
    print(f"\nFound {len(response['logStreams'])} recent log streams\n")
    
    # Get logs from the most recent stream
    latest_stream = response['logStreams'][0]
    stream_name = latest_stream['logStreamName']
    last_event = datetime.fromtimestamp(latest_stream['lastEventTimestamp'] / 1000)
    
    print(f"Latest stream: {stream_name}")
    print(f"Last event: {last_event.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("\n" + "-" * 80)
    
    # Get log events
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
    print("\nPossible reasons:")
    print("  • Crawler hasn't been invoked yet")
    print("  • Log group doesn't exist")
    print("  • Permissions issue")
