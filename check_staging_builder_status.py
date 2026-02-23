import boto3
from decimal import Decimal

# Connect to staging DynamoDB table
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

# Scan for Builder.AWS posts
response = table.scan(
    FilterExpression='#src = :builder',
    ExpressionAttributeNames={'#src': 'source'},
    ExpressionAttributeValues={':builder': 'builder.aws.com'}
)

posts = response['Items']

# Count posts by status
total = len(posts)
with_authors = sum(1 for p in posts if p.get('authors') and p['authors'] != 'AWS Builder Community')
with_summaries = sum(1 for p in posts if p.get('summary'))
with_labels = sum(1 for p in posts if p.get('label'))
with_content = sum(1 for p in posts if p.get('content') and len(p['content']) > 100)

print(f"\n{'='*80}")
print(f"Builder.AWS Posts Status in Staging")
print(f"{'='*80}")
print(f"Total posts: {total}")
print(f"Posts with real authors: {with_authors}/{total}")
print(f"Posts with content (>100 chars): {with_content}/{total}")
print(f"Posts with summaries: {with_summaries}/{total}")
print(f"Posts with labels: {with_labels}/{total}")
print(f"{'='*80}\n")

# Show sample of posts without summaries
posts_without_summaries = [p for p in posts if not p.get('summary')]
if posts_without_summaries:
    print(f"\nSample posts WITHOUT summaries (showing first 5):")
    for i, post in enumerate(posts_without_summaries[:5], 1):
        print(f"\n{i}. {post.get('title', 'No title')}")
        print(f"   Post ID: {post['post_id']}")
        print(f"   Author: {post.get('authors', 'No author')}")
        print(f"   Has content: {bool(post.get('content') and len(post['content']) > 100)}")
        print(f"   Content length: {len(post.get('content', ''))}")
