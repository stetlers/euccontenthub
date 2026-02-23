#!/usr/bin/env python3
"""
Verify that all Builder.AWS posts have summaries and labels
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts')

print("="*80)
print("VERIFYING RESTORATION COMPLETE")
print("="*80)

# Get all Builder posts
response = table.scan(
    FilterExpression='begins_with(post_id, :prefix)',
    ExpressionAttributeValues={':prefix': 'builder-'}
)

posts = response['Items']
print(f"\nTotal Builder.AWS posts: {len(posts)}")

# Check each post
missing_summary = []
missing_label = []
sample_posts = []

for post in posts:
    post_id = post['post_id']
    has_summary = bool(post.get('summary', '').strip())
    has_label = bool(post.get('label', '').strip())
    
    if not has_summary:
        missing_summary.append(post_id)
    if not has_label:
        missing_label.append(post_id)
    
    # Collect samples
    if len(sample_posts) < 5:
        sample_posts.append({
            'id': post_id,
            'title': post.get('title', 'N/A')[:60],
            'authors': post.get('authors', 'N/A'),
            'summary': post.get('summary', 'N/A')[:80],
            'label': post.get('label', 'N/A')
        })

print(f"\nPosts WITH summaries: {len(posts) - len(missing_summary)}")
print(f"Posts WITHOUT summaries: {len(missing_summary)}")
print(f"\nPosts WITH labels: {len(posts) - len(missing_label)}")
print(f"Posts WITHOUT labels: {len(missing_label)}")

if missing_summary:
    print(f"\n⚠️  Posts missing summaries:")
    for post_id in missing_summary[:10]:
        print(f"  - {post_id}")
    if len(missing_summary) > 10:
        print(f"  ... and {len(missing_summary) - 10} more")

if missing_label:
    print(f"\n⚠️  Posts missing labels:")
    for post_id in missing_label[:10]:
        print(f"  - {post_id}")
    if len(missing_label) > 10:
        print(f"  ... and {len(missing_label) - 10} more")

print("\n" + "="*80)
print("SAMPLE POSTS (showing 5 random posts)")
print("="*80)

for i, post in enumerate(sample_posts, 1):
    print(f"\n{i}. {post['title']}...")
    print(f"   ID: {post['id']}")
    print(f"   Authors: {post['authors']}")
    print(f"   Summary: {post['summary']}...")
    print(f"   Label: {post['label']}")

if not missing_summary and not missing_label:
    print("\n" + "="*80)
    print("✓ ALL POSTS HAVE SUMMARIES AND LABELS!")
    print("="*80)
    print("\nRestoration is 100% complete.")
else:
    print("\n" + "="*80)
    print("⚠️  RESTORATION INCOMPLETE")
    print("="*80)
    print(f"\nStill need to restore:")
    print(f"  - {len(missing_summary)} summaries")
    print(f"  - {len(missing_label)} labels")
