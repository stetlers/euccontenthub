import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('aws-blog-posts')

# Scan ALL posts (handle pagination)
print("Scanning production table for posts without summaries...")
posts_without_summaries = []
posts_with_summaries = []

response = table.scan(
    ProjectionExpression='post_id, title, summary',
    FilterExpression='attribute_not_exists(summary) OR summary = :empty',
    ExpressionAttributeValues={':empty': ''}
)

posts_without_summaries.extend(response['Items'])

# Handle pagination
while 'LastEvaluatedKey' in response:
    response = table.scan(
        ProjectionExpression='post_id, title, summary',
        FilterExpression='attribute_not_exists(summary) OR summary = :empty',
        ExpressionAttributeValues={':empty': ''},
        ExclusiveStartKey=response['LastEvaluatedKey']
    )
    posts_without_summaries.extend(response['Items'])

# Count total posts
total_response = table.scan(Select='COUNT')
total_count = total_response['Count']
while 'LastEvaluatedKey' in total_response:
    total_response = table.scan(
        Select='COUNT',
        ExclusiveStartKey=total_response['LastEvaluatedKey']
    )
    total_count += total_response['Count']

print(f"\nProduction Table Status:")
print(f"  Total posts: {total_count}")
print(f"  Posts WITHOUT summaries: {len(posts_without_summaries)}")
print(f"  Posts WITH summaries: {total_count - len(posts_without_summaries)}")
print(f"  Percentage with summaries: {(total_count - len(posts_without_summaries)) / total_count * 100:.1f}%")

if posts_without_summaries:
    print(f"\nFirst 10 posts without summaries:")
    for i, post in enumerate(posts_without_summaries[:10], 1):
        title = post.get('title', 'No title')[:60]
        print(f"  {i}. {title}...")
