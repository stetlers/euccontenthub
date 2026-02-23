"""
Monitor the full orchestration test in staging
Tracks: Sitemap Crawler → ECS Task → Summaries → Classifier
"""
import boto3
import time
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')
ecs_client = boto3.client('ecs', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("=" * 80)
print("ORCHESTRATION MONITORING - STAGING")
print("=" * 80)
print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Step 1: Check sitemap crawler logs
print("STEP 1: Checking Sitemap Crawler Logs")
print("-" * 80)

try:
    # Get recent log events from crawler
    log_group = '/aws/lambda/aws-blog-crawler'
    
    # Get the most recent log stream
    streams = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=1
    )
    
    if streams['logStreams']:
        stream_name = streams['logStreams'][0]['logStreamName']
        print(f"Latest log stream: {stream_name}")
        
        # Get recent events
        events = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            startTime=int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000),
            startFromHead=False
        )
        
        # Look for key messages
        ecs_task_id = None
        changed_posts = 0
        
        for event in events['events'][-50:]:  # Last 50 events
            message = event['message']
            
            if 'Builder.AWS posts changed' in message:
                print(f"✓ {message.strip()}")
                # Extract count
                try:
                    changed_posts = int(message.split()[0])
                except:
                    pass
            
            elif 'Started ECS task:' in message:
                print(f"✓ {message.strip()}")
                # Extract task ID
                try:
                    ecs_task_id = message.split('Started ECS task:')[1].strip()
                except:
                    pass
            
            elif 'Processing' in message and 'posts' in message:
                print(f"✓ {message.strip()}")
        
        if ecs_task_id:
            print(f"\n✅ ECS Task Started: {ecs_task_id}")
            
            # Step 2: Monitor ECS task
            print("\n" + "=" * 80)
            print("STEP 2: Monitoring ECS Task")
            print("-" * 80)
            
            # Check task status
            try:
                tasks = ecs_client.describe_tasks(
                    cluster='selenium-crawler-cluster',
                    tasks=[f'arn:aws:ecs:us-east-1:031421429609:task/selenium-crawler-cluster/{ecs_task_id}']
                )
                
                if tasks['tasks']:
                    task = tasks['tasks'][0]
                    status = task['lastStatus']
                    print(f"Task Status: {status}")
                    
                    if status == 'RUNNING':
                        print("⏳ Task is currently running...")
                        print("   Check logs: /ecs/selenium-crawler")
                    elif status == 'STOPPED':
                        exit_code = task['containers'][0].get('exitCode', 'N/A')
                        print(f"Task Exit Code: {exit_code}")
                        
                        if exit_code == 0:
                            print("✅ ECS task completed successfully!")
                        else:
                            print(f"❌ ECS task failed with exit code {exit_code}")
                
            except Exception as e:
                print(f"⚠️  Could not check ECS task status: {e}")
        
        else:
            print("\n⚠️  No ECS task ID found in logs yet")
            print("   The crawler may still be processing or no posts changed")
    
    else:
        print("⚠️  No recent log streams found")

except Exception as e:
    print(f"❌ Error checking crawler logs: {e}")

# Step 3: Check DynamoDB for results
print("\n" + "=" * 80)
print("STEP 3: Checking DynamoDB Results")
print("-" * 80)

try:
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
    
    if posts:
        # Analyze posts
        with_real_authors = [p for p in posts if p.get('authors') != 'AWS Builder Community']
        with_summaries = [p for p in posts if p.get('summary')]
        with_labels = [p for p in posts if p.get('label')]
        
        print(f"Posts with real authors: {len(with_real_authors)}/{len(posts)}")
        print(f"Posts with summaries: {len(with_summaries)}/{len(posts)}")
        print(f"Posts with labels: {len(with_labels)}/{len(posts)}")
        
        # Show sample
        if with_real_authors:
            print("\nSample posts with real authors:")
            for post in with_real_authors[:3]:
                print(f"  • {post.get('title', 'No title')[:60]}")
                print(f"    Author: {post.get('authors')}")
                print(f"    Has summary: {'Yes' if post.get('summary') else 'No'}")
                print(f"    Has label: {'Yes' if post.get('label') else 'No'}")
        
        # Check if orchestration is complete
        if len(posts) > 0:
            if len(with_real_authors) == len(posts):
                print("\n✅ All posts have real authors (ECS crawler worked!)")
            if len(with_summaries) == len(posts):
                print("✅ All posts have summaries (Summary generator worked!)")
            if len(with_labels) == len(posts):
                print("✅ All posts have labels (Classifier worked!)")
            
            if len(with_real_authors) == len(with_summaries) == len(with_labels) == len(posts):
                print("\n" + "=" * 80)
                print("🎉 FULL ORCHESTRATION SUCCESSFUL!")
                print("=" * 80)
                print("Sitemap → ECS → Summaries → Classifier all working!")
    else:
        print("⚠️  No Builder.AWS posts found yet")
        print("   The crawler may still be running")

except Exception as e:
    print(f"❌ Error checking DynamoDB: {e}")

print("\n" + "=" * 80)
print("Monitoring complete")
print("=" * 80)
