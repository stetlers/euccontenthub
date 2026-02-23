#!/usr/bin/env python3
"""
Diagnose why Builder.AWS posts are not being restored with summaries/labels
"""
import boto3
from datetime import datetime, timedelta

print("="*80)
print("PRODUCTION RESTORATION DIAGNOSIS")
print("="*80)

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')
ecs_client = boto3.client('ecs', region_name='us-east-1')
logs_client = boto3.client('logs', region_name='us-east-1')

# 1. Check current state of Builder posts
print("\n1. CURRENT STATE OF BUILDER POSTS")
print("-" * 80)
table = dynamodb.Table('aws-blog-posts')
response = table.scan(
    FilterExpression='begins_with(post_id, :prefix)',
    ExpressionAttributeValues={':prefix': 'builder-'}
)

posts = response['Items']
total = len(posts)
with_summary = sum(1 for p in posts if p.get('summary', '').strip())
with_label = sum(1 for p in posts if p.get('label', '').strip())
with_real_author = sum(1 for p in posts if p.get('authors', '') not in ['', 'Builder.AWS Team'])

print(f"Total Builder posts: {total}")
print(f"Posts WITH summaries: {with_summary} ({with_summary/total*100:.1f}%)")
print(f"Posts WITH labels: {with_label} ({with_label/total*100:.1f}%)")
print(f"Posts WITH real authors: {with_real_author} ({with_real_author/total*100:.1f}%)")

# 2. Check when posts were last crawled
print("\n2. RECENT CRAWLER ACTIVITY")
print("-" * 80)
recent_crawls = sorted(
    [(p['post_id'], p.get('last_crawled', 'Never')) for p in posts],
    key=lambda x: x[1],
    reverse=True
)[:5]

print("Most recently crawled posts:")
for post_id, last_crawled in recent_crawls:
    print(f"  {post_id}: {last_crawled}")

# 3. Check ECS tasks in last 24 hours
print("\n3. ECS SELENIUM CRAWLER TASKS (Last 24 hours)")
print("-" * 80)
try:
    # Get all tasks (running and stopped)
    running_tasks = ecs_client.list_tasks(
        cluster='selenium-crawler-cluster',
        desiredStatus='RUNNING'
    )
    
    stopped_tasks = ecs_client.list_tasks(
        cluster='selenium-crawler-cluster',
        desiredStatus='STOPPED',
        maxResults=10
    )
    
    print(f"Currently running: {len(running_tasks['taskArns'])}")
    print(f"Recently stopped: {len(stopped_tasks['taskArns'])}")
    
    if stopped_tasks['taskArns']:
        tasks = ecs_client.describe_tasks(
            cluster='selenium-crawler-cluster',
            tasks=stopped_tasks['taskArns']
        )
        
        print("\nRecent task details:")
        for task in tasks['tasks'][:3]:
            task_id = task['taskArn'].split('/')[-1][:20]
            created = task.get('createdAt', 'Unknown')
            stopped = task.get('stoppedAt', 'Unknown')
            exit_code = task['containers'][0].get('exitCode', 'N/A') if task.get('containers') else 'N/A'
            reason = task.get('stoppedReason', 'N/A')
            
            print(f"\n  Task: {task_id}...")
            print(f"    Created: {created}")
            print(f"    Stopped: {stopped}")
            print(f"    Exit Code: {exit_code}")
            if reason != 'Essential container in task exited':
                print(f"    Reason: {reason}")
    
except Exception as e:
    print(f"ERROR checking ECS: {e}")

# 4. Check ECS logs
print("\n4. ECS SELENIUM CRAWLER LOGS (Last hour)")
print("-" * 80)
try:
    start_time = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
    response = logs_client.filter_log_events(
        logGroupName='/ecs/selenium-crawler',
        startTime=start_time,
        limit=50
    )
    
    if response['events']:
        print(f"Found {len(response['events'])} log events")
        
        # Show key events
        for event in response['events'][-10:]:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            if any(kw in message for kw in ['posts updated', 'invoking', 'ERROR', 'Updated:', 'Failed']):
                print(f"  [{timestamp.strftime('%H:%M:%S')}] {message}")
    else:
        print("❌ NO LOGS FOUND - ECS tasks are not running!")
        
except Exception as e:
    print(f"ERROR checking logs: {e}")

# 5. Check Summary Generator logs
print("\n5. SUMMARY GENERATOR LOGS (Last hour)")
print("-" * 80)
try:
    start_time = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
    response = logs_client.filter_log_events(
        logGroupName='/aws/lambda/aws-blog-summary-generator',
        startTime=start_time,
        limit=50
    )
    
    if response['events']:
        print(f"Found {len(response['events'])} log events")
        
        # Count invocations
        invocations = sum(1 for e in response['events'] if 'Starting summary generation' in e['message'])
        print(f"Invocations in last hour: {invocations}")
        
        # Show key events
        for event in response['events'][-10:]:
            message = event['message'].strip()
            if any(kw in message for kw in ['Starting', 'Complete', 'generated', 'ERROR', 'Invoking classifier']):
                print(f"  {message}")
    else:
        print("❌ NO LOGS FOUND - Summary generator not invoked!")
        
except Exception as e:
    print(f"ERROR checking logs: {e}")

# 6. Check Classifier logs
print("\n6. CLASSIFIER LOGS (Last hour)")
print("-" * 80)
try:
    start_time = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
    response = logs_client.filter_log_events(
        logGroupName='/aws/lambda/aws-blog-classifier',
        startTime=start_time,
        limit=50
    )
    
    if response['events']:
        print(f"Found {len(response['events'])} log events")
        
        # Count invocations
        invocations = sum(1 for e in response['events'] if 'Starting classification' in e['message'])
        print(f"Invocations in last hour: {invocations}")
        
        # Show key events
        for event in response['events'][-10:]:
            message = event['message'].strip()
            if any(kw in message for kw in ['Starting', 'Complete', 'classified', 'ERROR']):
                print(f"  {message}")
    else:
        print("❌ NO LOGS FOUND - Classifier not invoked!")
        
except Exception as e:
    print(f"ERROR checking logs: {e}")

# 7. Check Lambda aliases
print("\n7. LAMBDA ALIAS CONFIGURATION")
print("-" * 80)
for func_name in ['enhanced-crawler', 'aws-blog-summary-generator', 'aws-blog-classifier']:
    try:
        response = lambda_client.get_alias(
            FunctionName=func_name,
            Name='production'
        )
        print(f"{func_name}: production → v{response['FunctionVersion']}")
    except Exception as e:
        print(f"{func_name}: ERROR - {e}")

print("\n" + "="*80)
print("DIAGNOSIS SUMMARY")
print("="*80)
print("\nThe restoration chain should work like this:")
print("1. Sitemap crawler detects changed posts")
print("2. Sitemap crawler invokes ECS Selenium crawler")
print("3. ECS Selenium crawler updates posts with real authors/content")
print("4. ECS Selenium crawler invokes Summary Generator")
print("5. Summary Generator creates summaries")
print("6. Summary Generator invokes Classifier")
print("7. Classifier adds labels")
print("\nCheck above to see where the chain is breaking!")
