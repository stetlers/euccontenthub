import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts')

print("Checking builder.aws posts for summary/label status...\n")

# Scan for builder.aws posts
response = table.scan(
    FilterExpression='begins_with(post_id, :prefix)',
    ExpressionAttributeValues={':prefix': 'builder-'}
)

posts = response['Items']
print(f"Total builder.aws posts: {len(posts)}\n")

# Categorize posts
with_summary = []
without_summary = []
with_label = []
without_label = []

for post in posts:
    has_summary = bool(post.get('summary', '').strip())
    has_label = bool(post.get('label', '').strip())
    
    if has_summary:
        with_summary.append(post)
    else:
        without_summary.append(post)
    
    if has_label:
        with_label.append(post)
    else:
        without_label.append(post)

print(f"Posts WITH summaries: {len(with_summary)}")
print(f"Posts WITHOUT summaries: {len(without_summary)}")
print(f"Posts WITH labels: {len(with_label)}")
print(f"Posts WITHOUT labels: {len(without_label)}\n")

# Check last_crawled dates to see when they were updated
print("Checking last_crawled dates for posts without summaries:")
for post in without_summary[:10]:
    last_crawled = post.get('last_crawled', 'N/A')
    date_updated = post.get('date_updated', 'N/A')
    print(f"  {post['post_id']}: last_crawled={last_crawled}, date_updated={date_updated}")

print("\n" + "="*80)
print("DIAGNOSIS:")
print("="*80)
print(f"If last_crawled dates are recent (today/yesterday), the crawler ran and")
print(f"detected these posts as 'changed', which wiped their summaries/labels.")
print(f"\nThe issue is in enhanced_crawler_lambda.py lines 563-571:")
print(f"When content_changed=True, it sets summary='', label='', etc.")
