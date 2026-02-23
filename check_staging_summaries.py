import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('aws-blog-posts-staging')

# Count posts with summaries
response = table.scan(
    FilterExpression='attribute_exists(summary) AND summary <> :empty',
    ExpressionAttributeValues={':empty': ''}
)
posts_with_summaries = len(response['Items'])

# Count total posts
total_response = table.scan(Select='COUNT')
total_posts = total_response['Count']

print(f"Staging Table Status:")
print(f"  Total posts: {total_posts}")
print(f"  Posts with summaries: {posts_with_summaries}")
print(f"  Posts without summaries: {total_posts - posts_with_summaries}")
print(f"  Percentage with summaries: {posts_with_summaries / total_posts * 100:.1f}%")
