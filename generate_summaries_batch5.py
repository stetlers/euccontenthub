"""
Generate summaries for posts missing them using batch_size=5
This is the recommended batch size for posts with up to 3000 characters
"""
import boto3
import time

lambda_client = boto3.client('lambda', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')

# Check production table
table = dynamodb.Table('aws-blog-posts')
response = table.scan(
    FilterExpression='attribute_not_exists(summary) OR summary = :empty',
    ExpressionAttributeValues={':empty': ''},
    Select='COUNT'
)

posts_needing_summaries = response['Count']
print(f"Posts needing summaries: {posts_needing_summaries}")

if posts_needing_summaries == 0:
    print("✅ All posts have summaries!")
    exit(0)

# Calculate batches (5 posts per batch)
batch_size = 5
num_batches = (posts_needing_summaries + batch_size - 1) // batch_size

print(f"Will invoke {num_batches} batches of {batch_size} posts each")
print(f"Estimated time: {num_batches * 1.5:.1f} minutes")

confirm = input(f"\nProceed with {num_batches} batch invocations? (yes/no): ")
if confirm.lower() != 'yes':
    print("Cancelled")
    exit(0)

print("\nInvoking summary generator batches...")
for i in range(num_batches):
    response = lambda_client.invoke(
        FunctionName='aws-blog-summary-generator:production',
        InvocationType='Event',  # Async
        Payload=f'{{"batch_size": {batch_size}}}'
    )
    print(f"  ✓ Batch {i+1}/{num_batches} invoked (StatusCode: {response['StatusCode']})")
    time.sleep(2)  # 2-second delay between batches

print(f"\n✅ All {num_batches} batches invoked!")
print(f"Monitor progress: aws logs tail /aws/lambda/aws-blog-summary-generator --follow")
