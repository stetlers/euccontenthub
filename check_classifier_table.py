"""
Check which table the classifier is using
"""
import boto3
from datetime import datetime, timedelta

logs = boto3.client('logs', region_name='us-east-1')

print("Checking classifier table configuration...")
print("=" * 80)

response = logs.filter_log_events(
    logGroupName='/aws/lambda/aws-blog-classifier',
    startTime=int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
)

# Find START messages that show environment
for event in response['events']:
    msg = event['message'].strip()
    if 'Environment:' in msg or 'Using table:' in msg or 'START RequestId' in msg:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        print(f'{timestamp.strftime("%H:%M:%S")} | {msg}')
