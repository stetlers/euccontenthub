"""
Delete all Builder.AWS posts from staging table
This allows us to test the full orchestration from scratch
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("Fetching Builder.AWS posts from staging...")
print("=" * 80)

# Get all Builder.AWS posts
response = table.scan(
    FilterExpression='#src = :builder',
    ExpressionAttributeNames={'#src': 'source'},
    ExpressionAttributeValues={':builder': 'builder.aws.com'}
)

builder_posts = response['Items']

# Handle pagination
while 'LastEvaluatedKey' in response:
    response = table.scan(
        FilterExpression='#src = :builder',
        ExpressionAttributeNames={'#src': 'source'},
        ExpressionAttributeValues={':builder': 'builder.aws.com'},
        ExclusiveStartKey=response['LastEvaluatedKey']
    )
    builder_posts.extend(response['Items'])

print(f"Found {len(builder_posts)} Builder.AWS posts to delete\n")

if len(builder_posts) == 0:
    print("No posts to delete. Exiting.")
    exit(0)

# Confirm deletion
print("⚠️  WARNING: This will delete ALL Builder.AWS posts from staging!")
print("This is safe because we're in staging, but make sure you want to proceed.")
confirm = input("\nType 'DELETE' to confirm: ")

if confirm != 'DELETE':
    print("Deletion cancelled.")
    exit(0)

print("\nDeleting posts...")
deleted_count = 0
failed_count = 0

for post in builder_posts:
    post_id = post['post_id']
    try:
        table.delete_item(Key={'post_id': post_id})
        deleted_count += 1
        if deleted_count % 10 == 0:
            print(f"  Deleted {deleted_count}/{len(builder_posts)}...")
    except Exception as e:
        print(f"  ✗ Failed to delete {post_id}: {e}")
        failed_count += 1

print("\n" + "=" * 80)
print(f"✓ Deleted: {deleted_count} posts")
if failed_count > 0:
    print(f"✗ Failed: {failed_count} posts")

print("\nStaging table is now ready for full orchestration test!")
print("Next steps:")
print("1. Deploy updated crawler Lambda to staging")
print("2. Trigger crawler from staging website")
print("3. Verify: Sitemap → ECS → Summaries → Classifier")
