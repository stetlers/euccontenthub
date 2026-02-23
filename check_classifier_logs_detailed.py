"""
Check classifier logs in detail
"""
import boto3
from datetime import datetime, timedelta

logs = boto3.client('logs', region_name='us-east-1')

print("=" * 80)
print("CLASSIFIER LOGS (last hour)")
print("=" * 80)

try:
    response = logs.filter_log_events(
        logGroupName='/aws/lambda/aws-blog-classifier',
        startTime=int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
    )
    
    if response['events']:
        print(f"\nFound {len(response['events'])} log events\n")
        for event in response['events'][-50:]:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            print(f'{timestamp.strftime("%H:%M:%S")} | {event["message"].strip()}')
    else:
        print("\nNo logs found in last hour")
except Exception as e:
    print(f'Error: {e}')
