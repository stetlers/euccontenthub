"""
Trigger summary generation for posts missing summaries in production
"""

import boto3
import json
import time

lambda_client = boto3.client('lambda', region_name='us-east-1')

# Invoke summary generator for production
# It will automatically find posts without summaries
# 115 posts / 50 per batch = 3 batches

print("Triggering summary generation for production posts...")

num_batches = 3  # 115 posts / 50 per batch = 2.3, round up to 3

for i in range(num_batches):
    response = lambda_client.invoke(
        FunctionName='aws-blog-summary-generator:production',
        InvocationType='Event',  # Async
        Payload=json.dumps({
            'batch_size': 50,
            'force': False
        })
    )
    print(f"Batch {i+1}/{num_batches} invoked: {response['StatusCode']}")
    time.sleep(1)

print(f"\n✅ Invoked {num_batches} summary generation batches")
print("Summaries will be generated in the background (takes ~5-10 minutes)")
print("\nTo check progress:")
print("  aws logs tail /aws/lambda/aws-blog-summary-generator --follow")
