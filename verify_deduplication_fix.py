"""
Verify that the deduplication fix is working by checking for duplicate post IDs
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("Checking for duplicate Builder.AWS posts in staging...")
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

print(f"Total Builder.AWS posts: {len(posts)}")

# Check for duplicates by URL
urls = [p.get('url') for p in posts]
unique_urls = set(urls)

print(f"Unique URLs: {len(unique_urls)}")
print(f"Duplicate URLs: {len(urls) - len(unique_urls)}")

if len(urls) != len(unique_urls):
    print("\n⚠️  DUPLICATES FOUND:")
    from collections import Counter
    url_counts = Counter(urls)
    for url, count in url_counts.items():
        if count > 1:
            print(f"  • {url} (appears {count} times)")
else:
    print("\n✅ No duplicates found!")

# Check for duplicates by post_id
post_ids = [p.get('post_id') for p in posts]
unique_post_ids = set(post_ids)

print(f"\nUnique post IDs: {len(unique_post_ids)}")
print(f"Duplicate post IDs: {len(post_ids) - len(unique_post_ids)}")

if len(post_ids) != len(unique_post_ids):
    print("\n⚠️  DUPLICATE POST IDs FOUND:")
    from collections import Counter
    id_counts = Counter(post_ids)
    for post_id, count in id_counts.items():
        if count > 1:
            print(f"  • {post_id} (appears {count} times)")
else:
    print("\n✅ No duplicate post IDs found!")
