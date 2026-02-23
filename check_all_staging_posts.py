"""
Check all posts in staging (both AWS Blog and Builder.AWS)
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("Checking all posts in staging...")
print("=" * 80)

response = table.scan()
posts = response['Items']

# Handle pagination
while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    posts.extend(response['Items'])

print(f"Total posts: {len(posts)}\n")

# Categorize by source
aws_blog_posts = [p for p in posts if p.get('source') == 'aws.amazon.com']
builder_posts = [p for p in posts if p.get('source') == 'builder.aws.com']

print("BY SOURCE:")
print("-" * 80)
print(f"AWS Blog posts: {len(aws_blog_posts)}")
print(f"Builder.AWS posts: {len(builder_posts)}")

# Check summaries and labels
aws_with_summaries = [p for p in aws_blog_posts if p.get('summary')]
aws_with_labels = [p for p in aws_blog_posts if p.get('label')]
builder_with_summaries = [p for p in builder_posts if p.get('summary')]
builder_with_labels = [p for p in builder_posts if p.get('label')]

print("\nAWS BLOG POSTS:")
print("-" * 80)
print(f"✓ With summaries: {len(aws_with_summaries)}/{len(aws_blog_posts)}")
print(f"✓ With labels: {len(aws_with_labels)}/{len(aws_blog_posts)}")

print("\nBUILDER.AWS POSTS:")
print("-" * 80)
print(f"✓ With summaries: {len(builder_with_summaries)}/{len(builder_posts)}")
print(f"✓ With labels: {len(builder_with_labels)}/{len(builder_posts)}")

if aws_with_labels:
    print(f"\nSample AWS Blog posts with labels:")
    for post in aws_with_labels[:5]:
        print(f"  • {post.get('title', 'No title')[:60]}")
        print(f"    Label: {post.get('label')}")
        print(f"    Summary: {'Yes' if post.get('summary') else 'No'}")

if builder_with_summaries:
    print(f"\nBuilder.AWS posts with summaries (need labels):")
    for post in builder_with_summaries:
        print(f"  • {post.get('title', 'No title')[:60]}")
        print(f"    Summary: {post.get('summary', '')[:80]}...")
        print(f"    Label: {post.get('label', 'NONE')}")
