"""
Fix the remaining 5% of production posts without summaries

Manually triggers summary generator for posts that failed during initial load.
"""
import boto3
import json

lambda_client = boto3.client('lambda', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts')

print("=" * 80)
print("FIX REMAINING PRODUCTION POSTS")
print("=" * 80)

# Find posts without summaries
print("\n1. Scanning for posts without summaries...")
response = table.scan(
    FilterExpression='attribute_not_exists(summary) OR summary = :empty',
    ExpressionAttributeValues={':empty': ''}
)

posts_without_summary = response['Items']

while 'LastEvaluatedKey' in response:
    response = table.scan(
        FilterExpression='attribute_not_exists(summary) OR summary = :empty',
        ExpressionAttributeValues={':empty': ''},
        ExclusiveStartKey=response['LastEvaluatedKey']
    )
    posts_without_summary.extend(response['Items'])

print(f"   Found {len(posts_without_summary)} posts without summaries")

if len(posts_without_summary) == 0:
    print("\n✅ All posts have summaries! Nothing to fix.")
    exit(0)

# Show sample of posts
print(f"\n2. Sample posts without summaries:")
for i, post in enumerate(posts_without_summary[:5], 1):
    print(f"   {i}. {post['title'][:60]}...")

# Trigger summary generator
print(f"\n3. Triggering summary generator for {len(posts_without_summary)} posts...")

# Calculate number of batches (5 posts per batch)
batch_size = 5
num_batches = (len(posts_without_summary) + batch_size - 1) // batch_size

print(f"   Will invoke summary generator {num_batches} times (batch size: {batch_size})")

for i in range(num_batches):
    try:
        response = lambda_client.invoke(
            FunctionName='aws-blog-summary-generator:production',
            InvocationType='Event',  # Async
            Payload=json.dumps({
                'batch_size': batch_size,
                'force': False
            })
        )
        print(f"   ✓ Invoked batch {i+1}/{num_batches}")
    except Exception as e:
        print(f"   ✗ Error invoking batch {i+1}: {e}")

print("\n4. Summary generator invoked!")
print("   The auto-chain will process all remaining posts.")
print("   Check progress with: python check_production_status.py")

print("\n" + "=" * 80)
print("✅ Fix initiated - summaries will be generated in ~2-3 minutes")
print("=" * 80)
