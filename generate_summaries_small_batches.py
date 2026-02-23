"""
Generate summaries with small batch sizes to avoid timeouts
Rule: Small batch sizes (10), many batches
"""

import boto3
import json
import time

lambda_client = boto3.client('lambda', region_name='us-east-1')

# Small batch size to avoid timeouts
BATCH_SIZE = 10
POSTS_NEEDING_SUMMARIES = 64

num_batches = (POSTS_NEEDING_SUMMARIES + BATCH_SIZE - 1) // BATCH_SIZE

print(f"Generating summaries for {POSTS_NEEDING_SUMMARIES} posts")
print(f"Batch size: {BATCH_SIZE}")
print(f"Number of batches: {num_batches}")
print(f"\nStarting summary generation...")

for i in range(num_batches):
    try:
        response = lambda_client.invoke(
            FunctionName='aws-blog-summary-generator:production',
            InvocationType='Event',  # Async
            Payload=json.dumps({
                'batch_size': BATCH_SIZE,
                'force': False
            })
        )
        print(f"  Batch {i+1}/{num_batches} invoked: {response['StatusCode']}")
        time.sleep(2)  # Wait 2 seconds between batches
    except Exception as e:
        print(f"  Error invoking batch {i+1}: {e}")

print(f"\n✅ Invoked {num_batches} batches")
print(f"⏱️  Estimated completion time: {num_batches * 2} minutes")
print("\nTo monitor progress:")
print("  aws logs tail /aws/lambda/aws-blog-summary-generator --follow")
