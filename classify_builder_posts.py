"""
Classify the 5 Builder.AWS posts that have summaries
"""
import boto3
import json

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("=" * 80)
print("Finding Builder.AWS posts with summaries but no labels")
print("=" * 80)

# Scan for Builder.AWS posts
response = table.scan(
    FilterExpression='#src = :builder',
    ExpressionAttributeNames={'#src': 'source'},
    ExpressionAttributeValues={':builder': 'builder.aws.com'}
)

posts = response['Items']

# Handle pagination
while 'LastEvaluatedKey' in response:
    response = table.scan(
        FilterExpression='#src = :builder',
        ExpressionAttributeNames={'#src': 'source'},
        ExpressionAttributeValues={':builder': 'builder.aws.com'},
        ExclusiveStartKey=response['LastEvaluatedKey']
    )
    posts.extend(response['Items'])

# Find posts with summaries but no labels
posts_to_classify = [p for p in posts if p.get('summary') and not p.get('label')]

print(f"\nFound {len(posts_to_classify)} Builder.AWS posts with summaries but no labels\n")

if not posts_to_classify:
    print("No posts to classify!")
else:
    print("Invoking classifier for each post:")
    print("-" * 80)
    
    for post in posts_to_classify:
        post_id = post['post_id']
        title = post.get('title', 'No title')
        
        print(f"\n  • {title[:60]}")
        print(f"    Post ID: {post_id}")
        
        try:
            response = lambda_client.invoke(
                FunctionName='aws-blog-classifier:staging',
                InvocationType='Event',  # Async
                Payload=json.dumps({
                    'post_id': post_id,
                    'table_name': 'aws-blog-posts-staging'
                })
            )
            print(f"    ✓ Classifier invoked")
        except Exception as e:
            print(f"    ✗ Error: {e}")

print("\n" + "=" * 80)
print("Wait 30 seconds for classification to complete...")
print("Then check: python check_staging_status.py")
