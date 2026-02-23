import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("\n" + "="*80)
print("Posts Without Summaries in Staging")
print("="*80)

# Scan for posts without summaries
response = table.scan(
    FilterExpression='attribute_not_exists(summary) OR summary = :empty',
    ExpressionAttributeValues={':empty': ''}
)

posts = response['Items']

# Handle pagination
while 'LastEvaluatedKey' in response:
    response = table.scan(
        FilterExpression='attribute_not_exists(summary) OR summary = :empty',
        ExpressionAttributeValues={':empty': ''},
        ExclusiveStartKey=response['LastEvaluatedKey']
    )
    posts.extend(response['Items'])

print(f"\nTotal posts without summaries: {len(posts)}")

if posts:
    # Group by source
    by_source = {}
    for post in posts:
        source = post.get('source', 'unknown')
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(post)
    
    print("\nBreakdown by source:")
    for source, source_posts in by_source.items():
        print(f"  {source}: {len(source_posts)} posts")
    
    print(f"\nSample posts (first 10):")
    for i, post in enumerate(posts[:10], 1):
        print(f"\n{i}. {post.get('title', 'No title')}")
        print(f"   Post ID: {post['post_id']}")
        print(f"   Source: {post.get('source', 'unknown')}")
        print(f"   Has content: {bool(post.get('content'))}")
else:
    print("\n✅ All posts have summaries!")
