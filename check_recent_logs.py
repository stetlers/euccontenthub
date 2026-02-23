"""
Check recent logs for summary generator and classifier
"""
import boto3
from datetime import datetime, timedelta

logs = boto3.client('logs', region_name='us-east-1')

# Check summary generator logs
print('=' * 80)
print('SUMMARY GENERATOR LOGS (last 5 minutes)')
print('=' * 80)

try:
    response = logs.filter_log_events(
        logGroupName='/aws/lambda/aws-blog-summary-generator',
        startTime=int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)
    )
    
    if response['events']:
        for event in response['events'][-30:]:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            print(f'{timestamp.strftime("%H:%M:%S")} | {event["message"].strip()}')
    else:
        print("No recent logs found")
except Exception as e:
    print(f'Error: {e}')

print('\n' + '=' * 80)
print('CLASSIFIER LOGS (last 5 minutes)')
print('=' * 80)

try:
    response = logs.filter_log_events(
        logGroupName='/aws/lambda/aws-blog-classifier',
        startTime=int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)
    )
    
    if response['events']:
        for event in response['events'][-30:]:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            print(f'{timestamp.strftime("%H:%M:%S")} | {event["message"].strip()}')
    else:
        print("No recent logs found")
except Exception as e:
    print(f'Error: {e}')
