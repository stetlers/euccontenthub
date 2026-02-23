import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts')

# Get posts without summaries
print("Investigating posts without summaries...\n")
response = table.scan(
    FilterExpression='attribute_not_exists(summary) OR summary = :empty',
    ExpressionAttributeValues={':empty': ''}
)

posts_without_summaries = response['Items']

# Handle pagination
while 'LastEvaluatedKey' in response:
    response = table.scan(
        FilterExpression='attribute_not_exists(summary) OR summary = :empty',
        ExpressionAttributeValues={':empty': ''},
        ExclusiveStartKey=response['LastEvaluatedKey']
    )
    posts_without_summaries.extend(response['Items'])

print(f"Found {len(posts_without_summaries)} posts without summaries\n")
print("=" * 80)

for i, post in enumerate(posts_without_summaries, 1):
    print(f"\n{i}. {post.get('title', 'No title')}")
    print(f"   Post ID: {post.get('post_id', 'N/A')}")
    print(f"   Source: {post.get('source', 'N/A')}")
    print(f"   Date Published: {post.get('date_published', 'N/A')}")
    print(f"   Last Crawled: {post.get('last_crawled', 'Never')}")
    
    content = post.get('content', '')
    print(f"   Content Length: {len(content)} characters")
    
    if len(content) < 50:
        print(f"   ⚠️  ISSUE: Content too short ({len(content)} chars < 50 minimum)")
    
    if not content or content.strip() == '':
        print(f"   ⚠️  ISSUE: Content is empty or whitespace only")
    
    # Check if it's a Builder.AWS post with template content
    if 'Builder.AWS article' in content:
        print(f"   ⚠️  ISSUE: Builder.AWS post with template content only")
    
    print(f"   Content Preview: {content[:100]}...")

print("\n" + "=" * 80)
print("\nSUMMARY OF ISSUES:")
print("-" * 80)

# Analyze patterns
short_content = [p for p in posts_without_summaries if len(p.get('content', '')) < 50]
empty_content = [p for p in posts_without_summaries if not p.get('content', '').strip()]
builder_template = [p for p in posts_without_summaries if 'Builder.AWS article' in p.get('content', '')]

print(f"Posts with content < 50 chars: {len(short_content)}")
print(f"Posts with empty content: {len(empty_content)}")
print(f"Builder.AWS posts with template only: {len(builder_template)}")

if builder_template:
    print(f"\n⚠️  ROOT CAUSE: {len(builder_template)} Builder.AWS posts have template content only")
    print("   These posts need to be crawled with the Selenium crawler to get real content")
