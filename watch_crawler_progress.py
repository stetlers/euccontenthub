"""
Watch crawler progress in real-time
"""
import boto3
import time
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')
logs_client = boto3.client('logs', region_name='us-east-1')

print("=" * 80)
print("WATCHING CRAWLER PROGRESS")
print("=" * 80)
print("Press Ctrl+C to stop\n")

last_count = 0
check_interval = 10  # seconds

try:
    while True:
        # Check post count
        response = table.scan(
            FilterExpression='#src = :builder',
            ExpressionAttributeNames={'#src': 'source'},
            ExpressionAttributeValues={':builder': 'builder.aws.com'},
            Select='COUNT'
        )
        
        count = response['Count']
        
        # Handle pagination for count
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression='#src = :builder',
                ExpressionAttributeNames={'#src': 'source'},
                ExpressionAttributeValues={':builder': 'builder.aws.com'},
                Select='COUNT',
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            count += response['Count']
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if count != last_count:
            print(f"[{timestamp}] Builder.AWS posts: {count} (+{count - last_count})")
            last_count = count
        else:
            print(f"[{timestamp}] Builder.AWS posts: {count} (no change)")
        
        time.sleep(check_interval)

except KeyboardInterrupt:
    print("\n\nStopped monitoring.")
    print(f"\nFinal count: {last_count} Builder.AWS posts")
    print("\nRun 'python check_staging_status.py' for detailed status")
