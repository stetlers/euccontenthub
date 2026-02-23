#!/usr/bin/env python3
"""
Check the specific ECS task that was started
"""
import boto3
from datetime import datetime

ecs_client = boto3.client('ecs', region_name='us-east-1')
logs_client = boto3.client('logs', region_name='us-east-1')

task_id = 'b899db46b4774287946b8b48f4e88edc'

print("="*80)
print(f"CHECKING ECS TASK: {task_id}")
print("="*80)

# Get task details
try:
    response = ecs_client.describe_tasks(
        cluster='selenium-crawler-cluster',
        tasks=[f'arn:aws:ecs:us-east-1:031421429609:task/selenium-crawler-cluster/{task_id}']
    )
    
    if not response['tasks']:
        print(f"\nTask not found!")
        exit(1)
    
    task = response['tasks'][0]
    
    print(f"\nTask Status: {task['lastStatus']}")
    print(f"Desired Status: {task['desiredStatus']}")
    
    if task.get('createdAt'):
        print(f"Created: {task['createdAt']}")
    if task.get('startedAt'):
        print(f"Started: {task['startedAt']}")
    if task.get('stoppedAt'):
        print(f"Stopped: {task['stoppedAt']}")
    
    if task.get('stoppedReason'):
        print(f"Stopped Reason: {task['stoppedReason']}")
    
    if task.get('containers'):
        container = task['containers'][0]
        print(f"\nContainer Status: {container.get('lastStatus', 'Unknown')}")
        if container.get('exitCode') is not None:
            exit_code = container['exitCode']
            print(f"Exit Code: {exit_code}")
            if exit_code == 0:
                print("  ✓ SUCCESS")
            else:
                print(f"  ✗ FAILED")
        
        if container.get('reason'):
            print(f"Reason: {container['reason']}")
    
    # Get logs
    print("\n" + "="*80)
    print("TASK LOGS:")
    print("="*80 + "\n")
    
    try:
        log_stream = f"ecs/selenium-crawler/{task_id}"
        response = logs_client.get_log_events(
            logGroupName='/ecs/selenium-crawler',
            logStreamName=log_stream,
            startFromHead=True
        )
        
        if response['events']:
            for event in response['events']:
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message'].strip()
                print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
        else:
            print("No logs found")
            
    except logs_client.exceptions.ResourceNotFoundException:
        print("Log stream not found - task may not have started yet")
    except Exception as e:
        print(f"Error getting logs: {e}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
