"""
Trigger summary generator to process remaining posts without summaries
"""
import boto3
import time

lambda_client = boto3.client('lambda', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("=" * 80)
print("TRIGGERING SUMMARY GENERATOR FOR REMAINING POSTS")
print("=" * 80)

# Count posts without summaries
response = table.scan(
    FilterExpression='attribute_not_exists(summary) OR summary = :empty',
    ExpressionAttributeValues={':empty': ''}
)

posts_without_summaries = response['Count']

# Handle pagination
while 'LastEvaluatedKey' in response:
    response = table.scan(
        FilterExpression='attribute_not_exists(summary) OR summary = :empty',
        ExpressionAttributeValues={':empty': ''},
        ExclusiveStartKey=response['LastEvaluatedKey']
    )
    posts_without_summaries += response['Count']

print(f"\nPosts without summaries: {posts_without_summaries}")

if posts_without_summaries == 0:
    print("✅ All posts have summaries!")
    exit(0)

# Calculate number of batches needed (5 posts per batch)
batch_size = 5
num_batches = (posts_without_summaries + batch_size - 1) // batch_size

print(f"Invoking summary generator {num_batches} times (batch size: {batch_size})")
print()

# Invoke summary generator multiple times
for i in range(num_batches):
    try:
        lambda_client.invoke(
            FunctionName='aws-blog-summary-generator:staging',
            InvocationType='Event',  # Async
            Payload='{"batch_size": 5, "force": false, "table_name": "aws-blog-posts-staging"}'
        )
        print(f"  ✓ Invoked batch {i+1}/{num_batches}")
        time.sleep(0.5)  # Small delay between invocations
    except Exception as e:
        print(f"  ✗ Error invoking batch {i+1}: {e}")

print()
print("=" * 80)
print("✅ Summary generator invoked!")
print("=" * 80)
print("\nThe summary generator will process posts in batches.")
print("Wait a few minutes, then run: python check_staging_status.py")
