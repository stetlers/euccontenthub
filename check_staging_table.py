#!/usr/bin/env python3
"""Check what's in the staging table"""

import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

# Get total count
response = table.scan(Select='COUNT')
total_count = response['Count']

print(f"Total posts in staging: {total_count}")

# Get a few sample posts
response = table.scan(Limit=5)
posts = response.get('Items', [])

print(f"\nSample posts:")
for post in posts:
    print(f"  - {post.get('post_id')}: {post.get('title', 'No title')[:60]}...")
    print(f"    Source: {post.get('source', 'Unknown')}")
    print(f"    Date: {post.get('date_published', 'Unknown')}")
    print()

# Count by source
response = table.scan()
all_posts = response.get('Items', [])

aws_blog_count = sum(1 for p in all_posts if 'aws.amazon.com' in p.get('source', ''))
builder_count = sum(1 for p in all_posts if 'builder.aws.com' in p.get('source', ''))

print(f"Posts by source:")
print(f"  AWS Blog: {aws_blog_count}")
print(f"  Builder.AWS: {builder_count}")
