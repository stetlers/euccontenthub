"""
Test auto-chaining by removing summaries from some posts and triggering summary generator
"""
import boto3
import json
import time

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')
logs_client = boto3.client('logs', region_name='us-east-1')

table = dynamodb.Table('aws-blog-posts-staging')

print("\n" + "="*80)
print("Auto-Chain Test - Staging Environment")
print("="*80)

# Step 1: Remove summaries from 12 Builder.AWS posts (to test 3 batches of 5)
print("\n1. Removing summaries from 12 Builder.AWS posts...")

response = table.scan(
    FilterExpression='#src = :builder AND attribute_exists(summary)',
    ExpressionAttributeNames={'#src': 'source'},
    ExpressionAttributeValues={':builder': 'builder.aws.com'},
    Limit=12
)

posts_to_clear = response['Items'][:12]
print(f"   Found {len(posts_to_clear)} posts with summaries")

for post in posts_to_clear:
    table.update_item(
        Key={'post_id': post['post_id']},
        UpdateExpression='REMOVE summary, label'
    )
    print(f"   ✓ Cleared: {post['title'][:50]}...")

print(f"\n   Total cleared: {len(posts_to_clear)} posts")

# Step 2: Trigger summary generator with batch_size=5
print("\n2. Triggering summary generator (batch_size=5)...")
print("   Expected behavior:")
print("   - Batch 1: Process 5 posts, auto-chain")
print("   - Batch 2: Process 5 posts, auto-chain")
print("   - Batch 3: Process 2 posts, stop (no more posts)")

response = lambda_client.invoke(
    FunctionName='aws-blog-summary-generator:staging',
    InvocationType='Event',
    Payload=json.dumps({
        'batch_size': 5,
        'force': False,
        'table_name': 'aws-blog-posts-staging'
    })
)

print(f"   ✓ Lambda invoked (status: {response['StatusCode']})")

# Step 3: Wait and monitor logs
print("\n3. Monitoring logs for auto-chain behavior...")
print("   Waiting 60 seconds for processing to complete...")

time.sleep(60)

# Check logs for auto-chain messages
start_time = int((time.time() - 120) * 1000)  # Last 2 minutes
end_time = int(time.time() * 1000)

log_group = '/aws/lambda/aws-blog-summary-generator'

try:
    response = logs_client.filter_log_events(
        logGroupName=log_group,
        startTime=start_time,
        endTime=end_time,
        filterPattern='auto-chain'
    )
    
    if response['events']:
        print(f"\n   Found {len(response['events'])} auto-chain log entries:")
        for event in response['events'][-10:]:  # Show last 10
            message = event['message'].strip()
            if 'Auto-chain check' in message or 'Auto-chaining' in message or 'auto_chained' in message:
                print(f"   {message}")
    else:
        print("\n   ⚠️  No auto-chain log entries found")
        
except Exception as e:
    print(f"\n   Error checking logs: {e}")

# Step 4: Verify all posts have summaries again
print("\n4. Verifying final state...")
time.sleep(10)  # Wait a bit more for final batch

response = table.scan(
    FilterExpression='#src = :builder',
    ExpressionAttributeNames={'#src': 'source'},
    ExpressionAttributeValues={':builder': 'builder.aws.com'}
)

posts = response['Items']
with_summaries = sum(1 for p in posts if p.get('summary'))

print(f"   Builder.AWS posts: {len(posts)}")
print(f"   Posts with summaries: {with_summaries}/{len(posts)}")

if with_summaries == len(posts):
    print("\n✅ AUTO-CHAIN TEST PASSED!")
    print("   All posts have summaries, confirming auto-chaining worked correctly")
else:
    print(f"\n⚠️  AUTO-CHAIN TEST INCOMPLETE")
    print(f"   {len(posts) - with_summaries} posts still missing summaries")
    print("   May need more time or check logs for errors")

print("\n" + "="*80)
