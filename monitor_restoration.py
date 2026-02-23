#!/usr/bin/env python3
"""
Monitor the restoration of Builder.AWS posts
"""
import boto3
import time
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
ecs_client = boto3.client('ecs', region_name='us-east-1')
logs_client = boto3.client('logs', region_name='us-east-1')

def check_builder_posts():
    """Check status of Builder.AWS posts"""
    table = dynamodb.Table('aws-blog-posts')
    
    response = table.scan(
        FilterExpression='begins_with(post_id, :prefix)',
        ExpressionAttributeValues={':prefix': 'builder-'}
    )
    
    posts = response['Items']
    total = len(posts)
    with_summary = sum(1 for p in posts if p.get('summary', '').strip())
    with_label = sum(1 for p in posts if p.get('label', '').strip())
    
    return {
        'total': total,
        'with_summary': with_summary,
        'with_label': with_label,
        'missing_summary': total - with_summary,
        'missing_label': total - with_label
    }

def check_ecs_tasks():
    """Check running ECS tasks"""
    try:
        response = ecs_client.list_tasks(
            cluster='selenium-crawler-cluster',
            desiredStatus='RUNNING'
        )
        return len(response['taskArns'])
    except:
        return 0

def check_recent_logs():
    """Check for recent activity in logs"""
    try:
        start_time = int((datetime.now().timestamp() - 300) * 1000)  # Last 5 minutes
        
        # Check crawler logs
        crawler_response = logs_client.filter_log_events(
            logGroupName='/aws/lambda/aws-blog-crawler',
            startTime=start_time,
            limit=10
        )
        
        # Check ECS logs
        ecs_response = logs_client.filter_log_events(
            logGroupName='/ecs/selenium-crawler',
            startTime=start_time,
            limit=10
        )
        
        return {
            'crawler_active': len(crawler_response['events']) > 0,
            'ecs_active': len(ecs_response['events']) > 0
        }
    except:
        return {'crawler_active': False, 'ecs_active': False}

print("="*80)
print("MONITORING BUILDER.AWS POST RESTORATION")
print("="*80)
print("\nPress Ctrl+C to stop monitoring\n")

initial_stats = check_builder_posts()
print(f"Initial state:")
print(f"  Total posts: {initial_stats['total']}")
print(f"  With summaries: {initial_stats['with_summary']} ({initial_stats['with_summary']/initial_stats['total']*100:.1f}%)")
print(f"  Missing summaries: {initial_stats['missing_summary']}")
print(f"  With labels: {initial_stats['with_label']} ({initial_stats['with_label']/initial_stats['total']*100:.1f}%)")
print(f"  Missing labels: {initial_stats['missing_label']}")

print("\n" + "-"*80)
print("Monitoring progress (updates every 30 seconds)...")
print("-"*80 + "\n")

try:
    iteration = 0
    while True:
        iteration += 1
        time.sleep(30)
        
        stats = check_builder_posts()
        ecs_tasks = check_ecs_tasks()
        logs = check_recent_logs()
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Calculate progress
        summary_progress = stats['with_summary'] - initial_stats['with_summary']
        label_progress = stats['with_label'] - initial_stats['with_label']
        
        print(f"[{timestamp}] Update #{iteration}:")
        print(f"  Summaries: {stats['with_summary']}/{stats['total']} (+{summary_progress} since start)")
        print(f"  Labels: {stats['with_label']}/{stats['total']} (+{label_progress} since start)")
        print(f"  ECS tasks running: {ecs_tasks}")
        print(f"  Crawler active: {'✓' if logs['crawler_active'] else '✗'}")
        print(f"  ECS active: {'✓' if logs['ecs_active'] else '✗'}")
        
        # Check if complete
        if stats['missing_summary'] == 0 and stats['missing_label'] == 0:
            print("\n" + "="*80)
            print("✓ RESTORATION COMPLETE!")
            print("="*80)
            print(f"\nAll {stats['total']} Builder.AWS posts now have summaries and labels.")
            break
        
        print()

except KeyboardInterrupt:
    print("\n\nMonitoring stopped by user.")
    
    final_stats = check_builder_posts()
    summary_progress = final_stats['with_summary'] - initial_stats['with_summary']
    label_progress = final_stats['with_label'] - initial_stats['with_label']
    
    print("\n" + "="*80)
    print("FINAL STATUS")
    print("="*80)
    print(f"\nSummaries restored: {summary_progress}")
    print(f"Labels restored: {label_progress}")
    print(f"\nRemaining:")
    print(f"  Missing summaries: {final_stats['missing_summary']}")
    print(f"  Missing labels: {final_stats['missing_label']}")
