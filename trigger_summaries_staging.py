"""
Manually trigger summary generator for staging posts with real authors
"""
import boto3
import json

lambda_client = boto3.client('lambda', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("=" * 80)
print("Triggering Summary Generator for Staging")
print("=" * 80)

# Get Builder.AWS posts with real authors but no summaries
print("\nFinding posts that need summaries...")
response = table.scan(
    FilterExpression='#src = :builder AND attribute_not_exists(summary)',
    ExpressionAttributeNames={'#src': 'source'},
    ExpressionAttributeValues={':builder': 'builder.aws.com'}
)

posts = response['Items']

# Handle pagination
while 'LastEvaluatedKey' in response:
    response = table.scan(
        FilterExpression='#src = :builder AND attribute_not_exists(summary)',
        ExpressionAttributeNames={'#src': 'source'},
        ExpressionAttributeValues={':builder': 'builder.aws.com'},
        ExclusiveStartKey=response['LastEvaluatedKey']
    )
    posts.extend(response['Items'])

# Filter for posts with real authors
posts_with_authors = [p for p in posts if p.get('authors') != 'AWS Builder Community']

print(f"Found {len(posts_with_authors)} posts with real authors needing summaries")

if len(posts_with_authors) == 0:
    print("\nNo posts need summaries. Exiting.")
    exit(0)

# Calculate batches (5 posts per batch)
batch_size = 5
num_batches = (len(posts_with_authors) + batch_size - 1) // batch_size

print(f"\nInvoking summary generator:")
print(f"  Posts to process: {len(posts_with_authors)}")
print(f"  Batch size: {batch_size}")
print(f"  Number of batches: {num_batches}")
print()

# Invoke summary generator batches
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
        print(f"  ✓ Invoked batch {i+1}/{num_batches}")
    except Exception as e:
        print(f"  ✗ Failed to invoke batch {i+1}: {e}")

print("\n" + "=" * 80)
print("Summary generator invoked!")
print("=" * 80)
print("\nWait 30-60 seconds, then check:")
print("  python check_staging_status.py")
