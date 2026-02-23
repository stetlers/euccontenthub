"""
Check the end of crawler logs to see ECS invocation
"""
import boto3
from datetime import datetime, timedelta

logs = boto3.client('logs', region_name='us-east-1')

print("Checking end of crawler logs...")
print("=" * 80)

response = logs.filter_log_events(
    logGroupName='/aws/lambda/aws-blog-crawler',
    startTime=int((datetime.now() - timedelta(minutes=30)).timestamp() * 1000)
)

if response['events']:
    # Get last 100 events
    events = response['events'][-100:]
    for event in events:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        msg = event['message'].strip()
        # Only show relevant lines
        if any(keyword in msg for keyword in ['Builder.AWS', 'ECS', 'changed', 'Summary', 'task', 'batch']):
            print(f'{timestamp.strftime("%H:%M:%S")} | {msg}')
else:
    print("No logs found")
