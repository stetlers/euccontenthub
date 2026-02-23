"""
Check detailed status of Builder.AWS posts in staging
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("Checking Builder.AWS posts status in staging...")
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

print(f"Total posts: {len(posts)}\n")

# Categorize posts
with_real_authors = [p for p in posts if p.get('authors') != 'AWS Builder Community']
with_summaries = [p for p in posts if p.get('summary')]
with_labels = [p for p in posts if p.get('label')]

print("STATUS BREAKDOWN:")
print("-" * 80)
print(f"✓ Posts with real authors: {len(with_real_authors)}/{len(posts)}")
print(f"✓ Posts with summaries: {len(with_summaries)}/{len(posts)}")
print(f"✓ Posts with labels: {len(with_labels)}/{len(posts)}")

if with_real_authors:
    print(f"\nSample posts with real authors:")
    for post in with_real_authors[:5]:
        print(f"  • {post.get('title', 'No title')[:60]}")
        print(f"    Author: {post.get('authors')}")
        print(f"    Summary: {'Yes' if post.get('summary') else 'No'}")
        print(f"    Label: {post.get('label', 'None')}")

if with_summaries:
    print(f"\nSample posts with summaries:")
    for post in with_summaries[:3]:
        print(f"  • {post.get('title', 'No title')[:60]}")
        print(f"    Summary: {post.get('summary', '')[:100]}...")

print("\n" + "=" * 80)
print("NEXT STEPS:")
if len(with_real_authors) < len(posts):
    print(f"  • {len(posts) - len(with_real_authors)} posts still need real authors")
    print("  • Run crawler again to process remaining posts")
if len(with_summaries) < len(with_real_authors):
    print(f"  • {len(with_real_authors) - len(with_summaries)} posts with authors need summaries")
    print("  • Check summary generator logs")
if len(with_labels) < len(with_summaries):
    print(f"  • {len(with_summaries) - len(with_labels)} posts with summaries need labels")
    print("  • Check classifier logs")
