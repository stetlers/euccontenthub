"""
Comprehensive diagnosis of the 3% of posts without summaries
"""
import boto3
import json

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("\n" + "="*80)
print("Diagnosing Missing Summaries (The Final 3%)")
print("="*80)

# Get all posts
print("\n1. Scanning all posts...")
response = table.scan()
posts = response['Items']

while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    posts.extend(response['Items'])

total = len(posts)
print(f"   Total posts: {total}")

# Categorize posts
posts_with_good_summaries = []
posts_with_error_summaries = []
posts_without_summaries = []

for post in posts:
    summary = post.get('summary', '')
    
    if not summary:
        posts_without_summaries.append(post)
    elif 'Error generating summary' in summary or 'ThrottlingException' in summary:
        posts_with_error_summaries.append(post)
    else:
        posts_with_good_summaries.append(post)

print(f"\n2. Summary Status:")
print(f"   ✅ Good summaries: {len(posts_with_good_summaries)} ({len(posts_with_good_summaries)*100//total}%)")
print(f"   ❌ Error summaries: {len(posts_with_error_summaries)} ({len(posts_with_error_summaries)*100//total}%)")
print(f"   ⚠️  No summaries: {len(posts_without_summaries)} ({len(posts_without_summaries)*100//total}%)")

# Analyze posts with error summaries
if posts_with_error_summaries:
    print(f"\n3. Posts with Error Summaries ({len(posts_with_error_summaries)} posts):")
    print("   These have error messages saved as summaries (from before exponential backoff)")
    print("\n   Sample (first 5):")
    for i, post in enumerate(posts_with_error_summaries[:5], 1):
        print(f"\n   {i}. {post.get('title', 'No title')[:60]}...")
        print(f"      Post ID: {post['post_id']}")
        print(f"      Source: {post.get('source', 'unknown')}")
        print(f"      Summary: {post['summary'][:100]}...")

# Analyze posts without summaries
if posts_without_summaries:
    print(f"\n4. Posts Without Summaries ({len(posts_without_summaries)} posts):")
    print("   These have no summary field at all")
    print("\n   Sample (first 5):")
    for i, post in enumerate(posts_without_summaries[:5], 1):
        print(f"\n   {i}. {post.get('title', 'No title')[:60]}...")
        print(f"      Post ID: {post['post_id']}")
        print(f"      Source: {post.get('source', 'unknown')}")
        print(f"      Has content: {bool(post.get('content'))}")
        print(f"      Content length: {len(post.get('content', ''))}")

# Check if auto-chain would pick them up
print(f"\n5. Auto-Chain Analysis:")
posts_auto_chain_will_process = len(posts_without_summaries) + len(posts_with_error_summaries)
print(f"   Posts auto-chain WILL process: {len(posts_without_summaries)} (no summary field)")
print(f"   Posts auto-chain WON'T process: {len(posts_with_error_summaries)} (has summary field)")

# Recommendations
print(f"\n6. Recommendations:")
if posts_with_error_summaries:
    print(f"   ⚠️  {len(posts_with_error_summaries)} posts have error summaries")
    print(f"      Action: Run 'python fix_throttled_summaries.py' to clear them")
    print(f"      Then: Auto-chain will pick them up automatically")

if posts_without_summaries:
    print(f"   ⚠️  {len(posts_without_summaries)} posts have no summaries")
    print(f"      Action: Trigger summary generator manually")
    print(f"      Command: python trigger_staging_summaries.py")

if not posts_with_error_summaries and not posts_without_summaries:
    print(f"   ✅ All posts have summaries!")
    print(f"      No action needed - 100% complete!")

# Save detailed report
print(f"\n7. Saving detailed report...")
report = {
    'total_posts': total,
    'good_summaries': len(posts_with_good_summaries),
    'error_summaries': len(posts_with_error_summaries),
    'no_summaries': len(posts_without_summaries),
    'posts_with_errors': [
        {
            'post_id': p['post_id'],
            'title': p.get('title', 'No title'),
            'source': p.get('source', 'unknown'),
            'summary': p['summary'][:200]
        }
        for p in posts_with_error_summaries
    ],
    'posts_without_summaries': [
        {
            'post_id': p['post_id'],
            'title': p.get('title', 'No title'),
            'source': p.get('source', 'unknown'),
            'has_content': bool(p.get('content')),
            'content_length': len(p.get('content', ''))
        }
        for p in posts_without_summaries
    ]
}

with open('missing_summaries_report.json', 'w') as f:
    json.dump(report, f, indent=2, default=str)

print(f"   ✓ Report saved to: missing_summaries_report.json")

print("\n" + "="*80)
