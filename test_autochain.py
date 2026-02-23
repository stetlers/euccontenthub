"""
Test auto-chaining by invoking summary generator once
"""
import boto3
import json

lambda_client = boto3.client('lambda', region_name='us-east-1')

print("Testing auto-chaining...")
print("Invoking summary generator once (should auto-chain if working)")

response = lambda_client.invoke(
    FunctionName='aws-blog-summary-generator:staging',
    InvocationType='Event',  # Async
    Payload=json.dumps({
        'batch_size': 5,
        'force': False,
        'table_name': 'aws-blog-posts-staging'
    })
)

print(f"✓ Invoked summary generator")
print(f"Status: {response['StatusCode']}")
print("\nWait 30 seconds, then check logs to see if auto-chaining triggered:")
print("python check_summary_logs_extended.py")
