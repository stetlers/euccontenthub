"""
Check current production DynamoDB status
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts')

print("=" * 80)
print("PRODUCTION STATUS CHECK")
print("=" * 80)

# Scan all posts
response = table.scan()
posts = response['Items']

while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    posts.extend(response['Items'])

print(f"\nTotal posts: {len(posts)}")

# Count by source
aws_blog_posts = [p for p in posts if p.get('source') == 'aws.amazon.com']
builder_posts = [p for p in posts if p.get('source') == 'builder.aws.com']

print(f"  AWS Blog posts: {len(aws_blog_posts)}")
print(f"  Builder.AWS posts: {len(builder_posts)}")

# Count summaries
posts_with_summary = [p for p in posts if p.get('summary') and p['summary'].strip()]
posts_without_summary = [p for p in posts if not p.get('summary') or not p['summary'].strip()]
error_summaries = [p for p in posts if p.get('summary', '').startswith('Error generating summary')]

print(f"\nSummary Status:")
print(f"  [OK] With summaries: {len(posts_with_summary)} ({len(posts_with_summary)/len(posts)*100:.1f}%)")
print(f"  [WARN] Without summaries: {len(posts_without_summary)} ({len(posts_without_summary)/len(posts)*100:.1f}%)")
print(f"  [ERROR] Error summaries: {len(error_summaries)} ({len(error_summaries)/len(posts)*100:.1f}%)")

# Check Builder.AWS authors
builder_with_community = [p for p in builder_posts if p.get('authors') == 'AWS Builder Community']
builder_with_real_authors = [p for p in builder_posts if p.get('authors') and p['authors'] != 'AWS Builder Community']

print(f"\nBuilder.AWS Author Status:")
print(f"  [WARN] 'AWS Builder Community' (placeholder): {len(builder_with_community)}")
print(f"  [OK] Real author names: {len(builder_with_real_authors)}")

# Count labels
posts_with_label = [p for p in posts if p.get('label') and p['label'].strip()]
posts_without_label = [p for p in posts if not p.get('label') or not p['label'].strip()]

print(f"\nLabel Status:")
print(f"  [OK] With labels: {len(posts_with_label)} ({len(posts_with_label)/len(posts)*100:.1f}%)")
print(f"  [WARN] Without labels: {len(posts_without_label)} ({len(posts_without_label)/len(posts)*100:.1f}%)")

print("\n" + "=" * 80)
