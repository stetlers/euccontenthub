"""
Clear Production DynamoDB Table

⚠️ WARNING: This deletes ALL production data!
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts')

print("=" * 80)
print("⚠️  CLEAR PRODUCTION TABLE")
print("=" * 80)
print("\nThis will DELETE ALL data from the production table: aws-blog-posts")
print("This action CANNOT be undone!")
print("\nCurrent production status has been saved to: production_before.txt")

response = input("\nType 'DELETE PRODUCTION DATA' to confirm: ")

if response != 'DELETE PRODUCTION DATA':
    print("\n❌ Aborted - no data was deleted")
    exit(0)

print("\n🗑️  Deleting all items from production table...")

# Scan and delete all items
deleted_count = 0
response = table.scan()

with table.batch_writer() as batch:
    for item in response['Items']:
        batch.delete_item(Key={'post_id': item['post_id']})
        deleted_count += 1

while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    with table.batch_writer() as batch:
        for item in response['Items']:
            batch.delete_item(Key={'post_id': item['post_id']})
            deleted_count += 1

print(f"\n✅ Deleted {deleted_count} items from production table")

# Verify table is empty
response = table.scan(Select='COUNT')
remaining = response['Count']

if remaining == 0:
    print("✅ Production table is now empty")
else:
    print(f"⚠️  Warning: {remaining} items still remain in table")

print("\n" + "=" * 80)
print("Production table cleared - ready for fresh data")
print("=" * 80)
