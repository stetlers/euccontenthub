"""
Check summary generator progress and auto-chaining behavior
"""
import boto3
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

table = dynamodb.Table('aws-blog-posts-staging')
log_group = '/aws/lambda/aws-blog-summary-generator'

print("\n" + "="*80)
print("Summary Generator Progress Check")
print("="*80)

# Check current summary status
print("\n1. Current Summary Status:")
response = table.scan()
posts = response['Items']

while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    posts.extend(response['Items'])

total = len(posts)
with_summaries = sum(1 for p in posts if p.get('summary'))
without_summaries = total - with_summaries

print(f"   Total posts: {total}")
print(f"   With summaries: {with_summaries} ({with_summaries*100//total if total > 0 else 0}%)")
print(f"   Without summaries: {without_summaries}")

# Check recent Lambda invocations
print("\n2. Recent Lambda Invocations (last 10 minutes):")
start_time = int((datetime.now() - timedelta(minutes=10)).timestamp() * 1000)
end_time = int(datetime.now().timestamp() * 1000)

try:
    response = logs_client.filter_log_events(
        logGroupName=log_group,
        startTime=start_time,
        endTime=end_time,
        filterPattern='START RequestId'
    )
    
    invocations = response['events']
    print(f"   Found {len(invocations)} invocations")
    
    if invocations:
        for i, event in enumerate(invocations[-5:], 1):  # Show last 5
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            print(f"   {i}. [{timestamp.strftime('%H:%M:%S')}]")
    
except Exception as e:
    print(f"   Error: {e}")

# Check for auto-chain messages
print("\n3. Auto-Chain Activity:")
try:
    response = logs_client.filter_log_events(
        logGroupName=log_group,
        startTime=start_time,
        endTime=end_time,
        filterPattern='Auto-chain'
    )
    
    if response['events']:
        print(f"   Found {len(response['events'])} auto-chain log entries")
        for event in response['events'][-5:]:  # Show last 5
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            if 'Auto-chain check' in message or 'Auto-chaining' in message:
                print(f"   [{timestamp.strftime('%H:%M:%S')}] {message}")
    else:
        print("   No auto-chain activity detected yet")
        
except Exception as e:
    print(f"   Error: {e}")

# Check for errors
print("\n4. Recent Errors:")
try:
    response = logs_client.filter_log_events(
        logGroupName=log_group,
        startTime=start_time,
        endTime=end_time,
        filterPattern='ERROR'
    )
    
    if response['events']:
        print(f"   ⚠️  Found {len(response['events'])} errors:")
        for event in response['events'][-3:]:  # Show last 3
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            print(f"   [{timestamp.strftime('%H:%M:%S')}] {message[:100]}...")
    else:
        print("   ✅ No errors detected")
        
except Exception as e:
    print(f"   Error: {e}")

# Check summary generation rate
print("\n5. Summary Generation Rate:")
try:
    response = logs_client.filter_log_events(
        logGroupName=log_group,
        startTime=start_time,
        endTime=end_time,
        filterPattern='Summary generated'
    )
    
    if response['events']:
        print(f"   Generated {len(response['events'])} summaries in last 10 minutes")
        print(f"   Rate: ~{len(response['events'])/10:.1f} summaries/minute")
    else:
        print("   No summaries generated yet (may still be starting)")
        
except Exception as e:
    print(f"   Error: {e}")

# Estimate completion time
if without_summaries > 0 and with_summaries > 0:
    print("\n6. Estimated Completion:")
    # Assume 5 posts per batch, ~10 seconds per post
    batches_remaining = (without_summaries + 4) // 5
    seconds_per_batch = 50  # Conservative estimate
    estimated_seconds = batches_remaining * seconds_per_batch
    
    print(f"   Posts remaining: {without_summaries}")
    print(f"   Batches remaining: ~{batches_remaining}")
    print(f"   Estimated time: ~{estimated_seconds//60} minutes")

print("\n" + "="*80)
