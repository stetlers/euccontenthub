"""
Check which posts have real authors but no summaries
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("Finding posts with real authors but no summaries...")
print("=" * 80)

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

# Find posts with real authors but no summaries
posts_needing_summaries = [
    p for p in posts 
    if p.get('authors') != 'AWS Builder Community' and not p.get('summary')
]

print(f"\nFound {len(posts_needing_summaries)} posts with real authors but no summaries:\n")

for post in posts_needing_summaries:
    print(f"  • {post.get('title', 'No title')[:70]}")
    print(f"    Author: {post.get('authors')}")
    print(f"    Post ID: {post['post_id']}")
    print()
