"""
Monitor auto-chaining progress in real-time
"""
import boto3
import time
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
logs_client = boto3.client('logs', region_name='us-east-1')

table = dynamodb.Table('aws-blog-posts-staging')
log_group = '/aws/lambda/aws-blog-summary-generator'

print("\n" + "="*80)
print("Monitoring Auto-Chain Progress")
print("="*80)
print("\nExpected: ~9 batches (42 posts ÷ 5 per batch)")
print("Checking every 15 seconds for 3 minutes...\n")

start_time = time.time()
check_interval = 15  # seconds
max_duration = 180  # 3 minutes

initial_count = None
last_count = None

while time.time() - start_time < max_duration:
    # Check how many posts still need summaries
    response = table.scan(
        FilterExpression='attribute_not_exists(summary) OR summary = :empty',
        ExpressionAttributeValues={':empty': ''},
        Select='COUNT'
    )
    
    remaining = response['Count']
    
    # Handle pagination for count
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='attribute_not_exists(summary) OR summary = :empty',
            ExpressionAttributeValues={':empty': ''},
            Select='COUNT',
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        remaining += response['Count']
    
    if initial_count is None:
        initial_count = remaining
    
    elapsed = int(time.time() - start_time)
    processed = initial_count - remaining if initial_count else 0
    
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] Remaining: {remaining} | Processed: {processed} | Elapsed: {elapsed}s")
    
    if remaining == 0:
        print("\n✅ All posts processed!")
        break
    
    if last_count is not None and remaining == last_count:
        # No progress
        print("   (No change - auto-chaining may have stopped)")
    
    last_count = remaining
    
    if time.time() - start_time < max_duration:
        time.sleep(check_interval)

# Final check
print("\n" + "="*80)
print("Final Status")
print("="*80)

response = table.scan(
    FilterExpression='#src = :builder',
    ExpressionAttributeNames={'#src': 'source'},
    ExpressionAttributeValues={':builder': 'builder.aws.com'}
)

posts = response['Items']
with_summaries = sum(1 for p in posts if p.get('summary'))
with_labels = sum(1 for p in posts if p.get('label'))

print(f"\nBuilder.AWS posts: {len(posts)}")
print(f"Posts with summaries: {with_summaries}/{len(posts)}")
print(f"Posts with labels: {with_labels}/{len(posts)}")

if with_summaries == len(posts):
    print("\n✅ SUCCESS! All Builder.AWS posts have summaries and labels")
else:
    print(f"\n⚠️  {len(posts) - with_summaries} posts still need processing")
