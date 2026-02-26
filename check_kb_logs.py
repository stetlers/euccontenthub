"""
Check recent KB editor logs
"""
import boto3
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')
log_group = '/aws/lambda/aws-blog-api'

# Get logs from last 5 minutes
start_time = int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)

print("\n🔍 Checking Lambda logs for KB editor activity...")
print("=" * 60)

try:
    # Get recent log streams
    streams = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=3
    )
    
    for stream in streams['logStreams']:
        stream_name = stream['logStreamName']
        print(f"\n📄 Stream: {stream_name}")
        
        events = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            startTime=start_time,
            limit=50
        )
        
        for event in events['events']:
            message = event['message']
            if 'kb-document' in message.lower() or 'error' in message.lower() or 'exception' in message.lower():
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                print(f"\n[{timestamp}]")
                print(message[:1000])  # Truncate long messages
                
except Exception as e:
    print(f"Error: {e}")
