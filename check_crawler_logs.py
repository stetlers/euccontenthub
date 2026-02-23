"""
Check crawler Lambda logs from the most recent invocation
"""
import boto3
from datetime import datetime, timedelta

logs = boto3.client('logs', region_name='us-east-1')

print("=" * 80)
print("CRAWLER LAMBDA LOGS (last 5 minutes)")
print("=" * 80)

try:
    response = logs.filter_log_events(
        logGroupName='/aws/lambda/aws-blog-crawler',
        startTime=int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)
    )
    
    if response['events']:
        print(f"\nFound {len(response['events'])} log events\n")
        for event in response['events']:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            print(f'{timestamp.strftime("%H:%M:%S")} | {event["message"].strip()}')
    else:
        print("\nNo logs found in last 5 minutes")
        print("Checking last 30 minutes...")
        
        response = logs.filter_log_events(
            logGroupName='/aws/lambda/aws-blog-crawler',
            startTime=int((datetime.now() - timedelta(minutes=30)).timestamp() * 1000)
        )
        
        if response['events']:
            print(f"\nFound {len(response['events'])} log events\n")
            for event in response['events'][-50:]:
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                print(f'{timestamp.strftime("%H:%M:%S")} | {event["message"].strip()}')
        else:
            print("No logs found in last 30 minutes either")
            
except Exception as e:
    print(f'Error: {e}')
