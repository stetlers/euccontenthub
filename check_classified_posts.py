"""
Find posts that were recently classified
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("Finding recently classified posts...")
print("=" * 80)

response = table.scan()
posts = response['Items']

# Handle pagination
while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    posts.extend(response['Items'])

# Find posts with labels
posts_with_labels = [p for p in posts if p.get('label')]

print(f"Total posts: {len(posts)}")
print(f"Posts with labels: {len(posts_with_labels)}\n")

if posts_with_labels:
    print("Posts with labels:")
    print("-" * 80)
    for post in posts_with_labels[:15]:
        source = post.get('source', 'NO SOURCE')
        print(f"  • {post.get('title', 'No title')[:60]}")
        print(f"    Source: {source}")
        print(f"    Label: {post.get('label')}")
        print(f"    Summary: {'Yes' if post.get('summary') else 'No'}")
        print()
