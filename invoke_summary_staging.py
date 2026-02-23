"""
Simple script to invoke summary generator for staging table
"""
import boto3
import json

lambda_client = boto3.client('lambda', region_name='us-east-1')

print("=" * 80)
print("Invoking Summary Generator for Staging")
print("=" * 80)

# Invoke 4 batches (should cover 20 posts, we have 17)
num_batches = 4
batch_size = 5

print(f"\nInvoking {num_batches} batches (batch size: {batch_size})")
print()

for i in range(num_batches):
    try:
        response = lambda_client.invoke(
            FunctionName='aws-blog-summary-generator:staging',
            InvocationType='Event',  # Async
            Payload=json.dumps({
                'batch_size': batch_size,
                'force': False,
                'table_name': 'aws-blog-posts-staging'
            })
        )
        print(f"  ✓ Batch {i+1}/{num_batches} invoked")
    except Exception as e:
        print(f"  ✗ Batch {i+1} failed: {e}")

print("\n" + "=" * 80)
print("Summary generator invoked!")
print("=" * 80)
print("\nWait 30-60 seconds for summaries to generate...")
print("Then check: python check_staging_status.py")
