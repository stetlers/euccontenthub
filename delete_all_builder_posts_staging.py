"""
Delete ALL Builder.AWS posts from staging table to test complete flow
"""
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("=" * 80)
print("DELETING ALL BUILDER.AWS POSTS FROM STAGING")
print("=" * 80)

# Get all Builder.AWS posts
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

print(f"\nFound {len(posts)} Builder.AWS posts to delete")

if not posts:
    print("No posts to delete!")
    exit(0)

# Confirm deletion
print("\n⚠️  WARNING: This will delete ALL Builder.AWS posts from staging!")
confirm = input("Type 'DELETE' to confirm: ")

if confirm != 'DELETE':
    print("Cancelled.")
    exit(0)

# Delete posts
deleted = 0
failed = 0

for post in posts:
    try:
        table.delete_item(Key={'post_id': post['post_id']})
        deleted += 1
        if deleted % 10 == 0:
            print(f"  Deleted {deleted}/{len(posts)}...")
    except Exception as e:
        print(f"  Failed to delete {post['post_id']}: {e}")
        failed += 1

print("\n" + "=" * 80)
print("DELETION COMPLETE")
print("=" * 80)
print(f"✅ Deleted: {deleted}")
if failed > 0:
    print(f"❌ Failed: {failed}")

print("\n💡 Next steps:")
print("   1. Go to https://staging.awseuccontent.com")
print("   2. Click 'Start Crawling' button")
print("   3. Wait for crawler to complete")
print("   4. Run: python check_staging_status.py")
print("   5. Verify all posts have real authors, summaries, and labels")
