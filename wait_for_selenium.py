import boto3
import time
from datetime import datetime

logs_client = boto3.client('logs', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

print("=" * 60)
print("Waiting for Selenium Crawler to Complete")
print("=" * 60)

log_group = '/aws/lambda/aws-blog-builder-selenium-crawler'
test_post_id = 'builder-building-a-simple-content-summarizer-with-amazon-bedrock'

# Check if Selenium is still running
print("\n1. Checking Selenium crawler status...")

for i in range(10):  # Check 10 times over 5 minutes
    try:
        # Get most recent log stream
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=1
        )
        
        if streams_response['logStreams']:
            stream = streams_response['logStreams'][0]
            last_event = datetime.fromtimestamp(stream['lastEventTimestamp'] / 1000)
            time_diff = (datetime.now() - last_event).total_seconds()
            
            print(f"\n  Check {i+1}/10:")
            print(f"  Last log event: {last_event.strftime('%H:%M:%S')}")
            print(f"  Time since last event: {int(time_diff)}s")
            
            # Get last few log lines
            events_response = logs_client.get_log_events(
                logGroupName=log_group,
                logStreamName=stream['logStreamName'],
                limit=10,
                startFromHead=False
            )
            
            last_messages = [e['message'].strip() for e in events_response['events'][-3:] if e['message'].strip()]
            if last_messages:
                print(f"  Last message: {last_messages[-1][:80]}...")
            
            # Check if completed
            for msg in last_messages:
                if 'END RequestId' in msg or 'REPORT RequestId' in msg:
                    print(f"\n✓ Selenium crawler completed!")
                    break
            else:
                if time_diff > 60:
                    print(f"\n⚠ Selenium crawler may have timed out or crashed")
                    break
                else:
                    print(f"  Still running...")
                    time.sleep(30)
                    continue
            break
        
    except Exception as e:
        print(f"  Error: {e}")
        break

# Check test post
print("\n\n2. Checking test post in DynamoDB...")
table = dynamodb.Table('aws-blog-posts-staging')

try:
    response = table.get_item(Key={'post_id': test_post_id})
    
    if 'Item' in response:
        post = response['Item']
        print(f"\n✓ Post found")
        print(f"  Authors: {post.get('authors', 'N/A')}")
        print(f"  Content length: {len(post.get('content', ''))} chars")
        print(f"  Has Summary: {'Yes' if post.get('summary') else 'No'}")
        print(f"  Has Label: {'Yes' if post.get('label') else 'No'}")
        
        if post.get('authors') != 'AWS Builder Community':
            print(f"\n✓ SUCCESS: Real author detected!")
        else:
            print(f"\n⚠ Still has placeholder author")
    
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
