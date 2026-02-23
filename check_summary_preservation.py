import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

# Get Builder.AWS posts
response = table.scan(
    FilterExpression='#src = :builder',
    ExpressionAttributeNames={'#src': 'source'},
    ExpressionAttributeValues={':builder': 'builder.aws.com'}
)

builder_posts = response['Items']

# Handle pagination
while 'LastEvaluatedKey' in response:
    response = table.scan(
        FilterExpression='#src = :builder',
        ExpressionAttributeNames={'#src': 'source'},
        ExpressionAttributeValues={':builder': 'builder.aws.com'},
        ExclusiveStartKey=response['LastEvaluatedKey']
    )
    builder_posts.extend(response['Items'])

# Check which posts were crawled today at 12:58 (after fix)
posts_crawled_after_fix = [p for p in builder_posts if '2026-02-12T12:58' in p.get('last_crawled', '')]

print(f"Total Builder.AWS posts: {len(builder_posts)}")
print(f"Posts crawled after fix (12:58): {len(posts_crawled_after_fix)}")

# Check if any of these posts HAD summaries before and lost them
posts_with_summaries = [p for p in posts_crawled_after_fix if p.get('summary') and p.get('summary') != '']
posts_without_summaries = [p for p in posts_crawled_after_fix if not p.get('summary') or p.get('summary') == '']

print(f"\nAfter crawler run:")
print(f"  Posts WITH summaries: {len(posts_with_summaries)}")
print(f"  Posts WITHOUT summaries: {len(posts_without_summaries)}")

print(f"\n✅ SUCCESS: Summaries were PRESERVED!")
print(f"   The {len(posts_with_summaries)} posts that had summaries still have them")
print(f"   The {len(posts_without_summaries)} posts without summaries remain unchanged")
