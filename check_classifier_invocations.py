"""
Check if classifier Lambda was invoked recently
"""
import boto3
from datetime import datetime, timedelta

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

print("Checking classifier Lambda invocations...")
print("=" * 80)

# Get invocation metrics for last 10 minutes
response = cloudwatch.get_metric_statistics(
    Namespace='AWS/Lambda',
    MetricName='Invocations',
    Dimensions=[
        {
            'Name': 'FunctionName',
            'Value': 'aws-blog-classifier'
        }
    ],
    StartTime=datetime.now() - timedelta(minutes=10),
    EndTime=datetime.now(),
    Period=60,  # 1 minute periods
    Statistics=['Sum']
)

if response['Datapoints']:
    print("\nInvocations in last 10 minutes:")
    for datapoint in sorted(response['Datapoints'], key=lambda x: x['Timestamp']):
        timestamp = datapoint['Timestamp'].strftime('%H:%M:%S')
        count = int(datapoint['Sum'])
        print(f"  {timestamp}: {count} invocations")
else:
    print("\nNo invocations in last 10 minutes")

# Check for errors
response = cloudwatch.get_metric_statistics(
    Namespace='AWS/Lambda',
    MetricName='Errors',
    Dimensions=[
        {
            'Name': 'FunctionName',
            'Value': 'aws-blog-classifier'
        }
    ],
    StartTime=datetime.now() - timedelta(minutes=10),
    EndTime=datetime.now(),
    Period=60,
    Statistics=['Sum']
)

if response['Datapoints']:
    print("\nErrors in last 10 minutes:")
    for datapoint in sorted(response['Datapoints'], key=lambda x: x['Timestamp']):
        timestamp = datapoint['Timestamp'].strftime('%H:%M:%S')
        count = int(datapoint['Sum'])
        if count > 0:
            print(f"  {timestamp}: {count} errors")
