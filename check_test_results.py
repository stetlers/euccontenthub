import boto3
import time
from datetime import datetime, timedelta

# Initialize clients
logs_client = boto3.client('logs', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

print("=" * 60)
print("Checking Sitemap Crawler Test Results")
print("=" * 60)

# Check sitemap crawler logs
print("\n1. Checking sitemap crawler logs...")
log_group = '/aws/lambda/aws-blog-crawler'
start_time = int((datetime.now() - timedelta(minutes=10)).timestamp() * 1000)

try:
    response = logs_client.filter_log_events(
        logGroupName=log_group,
        startTime=start_time,
        filterPattern=''
    )
    
    # Look for key messages
    changed_posts = []
    selenium_invoked = False
    
    for event in response['events']:
        message = event['message']
        
        # Look for changed posts
        if 'changed' in message.lower() and 'builder' in message.lower():
            print(f"\n✓ Found: {message.strip()}")
            changed_posts.append(message)
        
        # Look for Selenium invocation
        if 'selenium' in message.lower() and 'invok' in message.lower():
            print(f"\n✓ Found: {message.strip()}")
            selenium_invoked = True
        
        # Look for our test post
        if 'building-a-simple-content-summarizer' in message.lower():
            print(f"\n✓ Test post found: {message.strip()}")
    
    print(f"\n\nSummary:")
    print(f"- Changed posts detected: {len(changed_posts)}")
    print(f"- Selenium crawler invoked: {selenium_invoked}")
    
except Exception as e:
    print(f"Error checking logs: {e}")

# Check the test post in DynamoDB
print("\n\n2. Checking test post in DynamoDB...")
table = dynamodb.Table('aws-blog-posts-staging')

try:
    response = table.get_item(
        Key={'post_id': 'builder-building-a-simple-content-summarizer-with-amazon-bedrock'}
    )
    
    if 'Item' in response:
        post = response['Item']
        print(f"\n✓ Post found in DynamoDB")
        print(f"  - Title: {post.get('title', 'N/A')}")
        print(f"  - Authors: {post.get('authors', 'N/A')}")
        print(f"  - Date Updated: {post.get('date_updated', 'N/A')}")
        print(f"  - Has Summary: {'Yes' if post.get('summary') else 'No'}")
        print(f"  - Has Label: {'Yes' if post.get('label') else 'No'}")
        print(f"  - Content length: {len(post.get('content', ''))} chars")
        
        # Check if it's still placeholder data
        if post.get('authors') == 'AWS Builder Community':
            print("\n⚠ WARNING: Still has placeholder author (Selenium not run yet)")
        else:
            print(f"\n✓ Real author detected: {post.get('authors')}")
    else:
        print("✗ Post not found in DynamoDB")
        
except Exception as e:
    print(f"Error checking DynamoDB: {e}")

print("\n" + "=" * 60)
