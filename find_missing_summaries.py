#!/usr/bin/env python3
"""
Find Builder.AWS posts missing summaries or labels
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts')

print("="*80)
print("FINDING POSTS MISSING SUMMARIES/LABELS")
print("="*80)

# Get all Builder posts
response = table.scan(
    FilterExpression='begins_with(post_id, :prefix)',
    ExpressionAttributeValues={':prefix': 'builder-'}
)

posts = response['Items']
print(f"\nTotal Builder.AWS posts: {len(posts)}")

# Find posts missing data
missing_summary = []
missing_label = []
missing_both = []

for post in posts:
    post_id = post['post_id']
    title = post.get('title', 'N/A')
    authors = post.get('authors', 'N/A')
    has_summary = bool(post.get('summary', '').strip())
    has_label = bool(post.get('label', '').strip())
    
    if not has_summary and not has_label:
        missing_both.append({
            'id': post_id,
            'title': title,
            'authors': authors
        })
    elif not has_summary:
        missing_summary.append({
            'id': post_id,
            'title': title,
            'authors': authors
        })
    elif not has_label:
        missing_label.append({
            'id': post_id,
            'title': title,
            'authors': authors
        })

print(f"\nPosts WITH summaries: {len(posts) - len(missing_summary) - len(missing_both)}")
print(f"Posts WITH labels: {len(posts) - len(missing_label) - len(missing_both)}")

print(f"\n" + "="*80)
print(f"POSTS MISSING BOTH SUMMARY AND LABEL: {len(missing_both)}")
print("="*80)

if missing_both:
    for post in missing_both:
        print(f"\n  {post['title'][:70]}")
        print(f"    ID: {post['id']}")
        print(f"    Authors: {post['authors']}")
else:
    print("\n  None")

print(f"\n" + "="*80)
print(f"POSTS MISSING ONLY SUMMARY: {len(missing_summary)}")
print("="*80)

if missing_summary:
    for post in missing_summary:
        print(f"\n  {post['title'][:70]}")
        print(f"    ID: {post['id']}")
        print(f"    Authors: {post['authors']}")
else:
    print("\n  None")

print(f"\n" + "="*80)
print(f"POSTS MISSING ONLY LABEL: {len(missing_label)}")
print("="*80)

if missing_label:
    for post in missing_label:
        print(f"\n  {post['title'][:70]}")
        print(f"    ID: {post['id']}")
        print(f"    Authors: {post['authors']}")
else:
    print("\n  None")

# Summary
total_missing = len(missing_both) + len(missing_summary) + len(missing_label)
print(f"\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\nTotal posts needing attention: {total_missing}")
print(f"  - Missing both: {len(missing_both)}")
print(f"  - Missing only summary: {len(missing_summary)}")
print(f"  - Missing only label: {len(missing_label)}")

if total_missing > 0:
    print(f"\nTo fix these posts, run:")
    print(f"  python generate_all_builder_summaries.py")
