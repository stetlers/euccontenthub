"""
Clear all posts from staging table for final end-to-end test
"""
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("\n" + "="*80)
print("FINAL END-TO-END TEST - Clearing Staging Table")
print("="*80)

# Get current count
print("\n1. Checking current posts in staging...")
response = table.scan(Select='COUNT')
current_count = response['Count']

while 'LastEvaluatedKey' in response:
    response = table.scan(
        Select='COUNT',
        ExclusiveStartKey=response['LastEvaluatedKey']
    )
    current_count += response['Count']

print(f"   Current posts: {current_count}")

if current_count == 0:
    print("\n✓ Table already empty, ready for test!")
    exit(0)

# Confirm deletion
print(f"\n⚠️  This will DELETE ALL {current_count} posts from staging")
print("   This is necessary for the final end-to-end test")
print("\n   After deletion, you will:")
print("   1. Visit https://staging.awseuccontent.com")
print("   2. Click 'Start Crawling' button")
print("   3. Wait for complete orchestration chain to finish")
print("   4. Verify all posts have authors, summaries, and labels")

response = input("\nProceed with deletion? (yes/no): ")

if response.lower() != 'yes':
    print("\n❌ Deletion cancelled")
    exit(0)

# Delete all posts
print("\n2. Deleting all posts from staging...")

# Scan and delete in batches
deleted_count = 0
response = table.scan()

while True:
    items = response.get('Items', [])
    
    if not items:
        break
    
    # Delete in batches of 25 (DynamoDB limit)
    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(Key={'post_id': item['post_id']})
            deleted_count += 1
            if deleted_count % 50 == 0:
                print(f"   Deleted {deleted_count}/{current_count} posts...")
    
    # Check for more items
    if 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    else:
        break

print(f"   ✓ Deleted {deleted_count} posts")

# Verify empty
print("\n3. Verifying table is empty...")
response = table.scan(Select='COUNT')
final_count = response['Count']

if final_count == 0:
    print("   ✓ Table is empty")
else:
    print(f"   ⚠️  Warning: {final_count} posts still remain")

print("\n" + "="*80)
print("✅ Staging Table Cleared - Ready for Final Test!")
print("="*80)

print("\nNext Steps:")
print("1. Visit: https://staging.awseuccontent.com")
print("2. Click: 'Start Crawling' button")
print("3. Monitor progress with: python monitor_final_test.py")
print("\nExpected Results:")
print("  - AWS Blog posts created with authors, summaries, labels")
print("  - Builder.AWS posts created with placeholder data")
print("  - ECS tasks extract real authors and content")
print("  - Summary generator auto-chains through all posts")
print("  - Classifier assigns labels to all posts")
print("  - NO errors, NO duplicates, NO missing data")
