import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

# Get Builder.AWS posts
print("Checking Builder.AWS posts in staging...\n")
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

print(f"Total Builder.AWS posts: {len(builder_posts)}\n")

# Check for issues
missing_authors = [p for p in builder_posts if p.get('authors') == 'AWS Builder Community']
missing_summaries = [p for p in builder_posts if not p.get('summary') or p.get('summary') == '']

print("CRITICAL ISSUES:")
print("=" * 80)
print(f"Posts with generic 'AWS Builder Community' author: {len(missing_authors)}")
print(f"Posts without summaries: {len(missing_summaries)}")

print("\nSample posts with generic author (first 5):")
for i, post in enumerate(missing_authors[:5], 1):
    print(f"{i}. {post.get('title', 'No title')[:60]}...")
    print(f"   Author: {post.get('authors')}")
    print(f"   Last crawled: {post.get('last_crawled', 'Never')}")
    print(f"   Has summary: {'Yes' if post.get('summary') else 'No'}")
    print()
