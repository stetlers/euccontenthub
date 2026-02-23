"""
Check recent summary generator logs
"""
import boto3
from datetime import datetime, timedelta

logs = boto3.client('logs', region_name='us-east-1')

print("Checking summary generator logs (last 15 minutes)...")
print("=" * 80)

response = logs.filter_log_events(
    logGroupName='/aws/lambda/aws-blog-summary-generator',
    startTime=int((datetime.now() - timedelta(minutes=15)).timestamp() * 1000)
)

if response['events']:
    print(f"\nFound {len(response['events'])} log events\n")
    for event in response['events'][-50:]:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        print(f'{timestamp.strftime("%H:%M:%S")} | {event["message"].strip()}')
else:
    print("\nNo logs found in last 10 minutes")
