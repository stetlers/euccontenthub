#!/usr/bin/env python3
"""
Check recent crawler invocations to see what happened
"""
import boto3
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')

print("="*80)
print("CHECKING RECENT CRAWLER INVOCATIONS")
print("="*80)

# Check both possible log groups
log_groups = [
    '/aws/lambda/aws-blog-crawler',
    '/aws/lambda/enhanced-crawler'
]

start_time = int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)

for log_group in log_groups:
    print(f"\n{log_group}:")
    print("-" * 80)
    
    try:
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            limit=100
        )
        
        if not response['events']:
            print("No logs in last 24 hours")
            continue
        
        print(f"Found {len(response['events'])} log events\n")
        
        # Look for key events
        messages = [e['message'] for e in response['events']]
        all_text = '\n'.join(messages)
        
        # Check for invocations
        if 'START RequestId' in all_text:
            invocations = all_text.count('START RequestId')
            print(f"✓ Invoked {invocations} times in last 24 hours")
        
        # Check for Builder.AWS crawling
        if 'CRAWLING BUILDER.AWS' in all_text:
            print(f"✓ Builder.AWS crawl initiated")
        
        # Check for changed posts
        if 'posts changed' in all_text.lower():
            # Extract the number
            for line in messages:
                if 'posts changed' in line.lower():
                    print(f"✓ {line.strip()}")
        
        # Check for ECS invocation
        if 'invoking ECS' in all_text.lower() or 'Started ECS task' in all_text:
            print(f"✓ ECS Selenium crawler invoked")
            
            # Count tasks started
            task_count = all_text.count('Started ECS task')
            if task_count > 0:
                print(f"  Started {task_count} ECS tasks")
        else:
            print(f"✗ ECS Selenium crawler NOT invoked")
        
        # Check for errors
        if 'ERROR' in all_text or 'Error' in all_text:
            print(f"\n⚠️  Errors detected:")
            for line in messages:
                if 'ERROR' in line or 'Error' in line:
                    print(f"  {line.strip()}")
        
        # Show last 10 log lines
        print(f"\nLast 10 log lines:")
        for event in response['events'][-10:]:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            print(f"  [{timestamp.strftime('%H:%M:%S')}] {message[:100]}")
        
    except logs_client.exceptions.ResourceNotFoundException:
        print("Log group does not exist")
    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "="*80)
print("KEY QUESTION")
print("="*80)
print("\nDid the crawler invoke ECS Selenium tasks?")
print("If NO, that's why summaries aren't being restored.")
