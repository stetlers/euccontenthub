"""
Manually invoke classifier for staging posts with summaries
"""
import boto3
import json

lambda_client = boto3.client('lambda', region_name='us-east-1')

print("=" * 80)
print("Invoking Classifier for Staging Posts")
print("=" * 80)

# Invoke classifier (it will find posts with summaries but no labels)
try:
    response = lambda_client.invoke(
        FunctionName='aws-blog-classifier:staging',
        InvocationType='Event',  # Async
        Payload=json.dumps({
            'batch_size': 10,
            'table_name': 'aws-blog-posts-staging'
        })
    )
    print("\n✓ Classifier invoked successfully")
except Exception as e:
    print(f"\n✗ Failed to invoke classifier: {e}")

print("\n" + "=" * 80)
print("Wait 30 seconds for labels to be generated...")
print("Then check: python check_staging_status.py")
