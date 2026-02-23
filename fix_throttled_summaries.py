"""
Fix posts that got error messages as summaries due to Bedrock throttling
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("\n" + "="*80)
print("Fixing Throttled Summaries")
print("="*80)

# Scan for posts with error summaries
print("\n1. Finding posts with error summaries...")
response = table.scan()
posts = response['Items']

while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    posts.extend(response['Items'])

# Find posts with error summaries
error_posts = []
for post in posts:
    summary = post.get('summary', '')
    if 'Error generating summary' in summary or 'ThrottlingException' in summary:
        error_posts.append(post)

print(f"   Found {len(error_posts)} posts with error summaries")

if not error_posts:
    print("\n✅ No posts with error summaries found!")
    exit(0)

# Show sample
print(f"\n   Sample posts (first 5):")
for i, post in enumerate(error_posts[:5], 1):
    print(f"   {i}. {post.get('title', 'No title')[:60]}...")

# Clear the error summaries
print(f"\n2. Clearing error summaries...")
fixed_count = 0

for post in error_posts:
    try:
        table.update_item(
            Key={'post_id': post['post_id']},
            UpdateExpression='REMOVE summary'
        )
        fixed_count += 1
        if fixed_count % 10 == 0:
            print(f"   Fixed {fixed_count}/{len(error_posts)}...")
    except Exception as e:
        print(f"   Error fixing {post['post_id']}: {e}")

print(f"   ✓ Fixed {fixed_count} posts")

print("\n" + "="*80)
print("✅ Error Summaries Cleared!")
print("="*80)
print(f"\nCleared {fixed_count} error summaries")
print("These posts will be picked up by the next auto-chain cycle")
print("\nThe summary generator is still running and will process these posts")
print("automatically as part of the ongoing auto-chain.")
