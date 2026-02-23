#!/usr/bin/env python3
"""
Check why ECS tasks are failing to start
"""
import boto3
from datetime import datetime, timedelta

ecs_client = boto3.client('ecs', region_name='us-east-1')

print("="*80)
print("CHECKING ECS TASK FAILURES")
print("="*80)

# Get recent stopped tasks
try:
    response = ecs_client.list_tasks(
        cluster='selenium-crawler-cluster',
        desiredStatus='STOPPED',
        maxResults=10
    )
    
    if not response['taskArns']:
        print("\nNo stopped tasks found")
        exit(0)
    
    # Get details
    tasks = ecs_client.describe_tasks(
        cluster='selenium-crawler-cluster',
        tasks=response['taskArns']
    )
    
    print(f"\nFound {len(tasks['tasks'])} stopped tasks\n")
    
    for task in tasks['tasks']:
        task_id = task['taskArn'].split('/')[-1]
        created = task.get('createdAt', 'Unknown')
        stopped = task.get('stoppedAt', 'Unknown')
        stopped_reason = task.get('stoppedReason', 'N/A')
        
        print(f"Task: {task_id}")
        print(f"  Created: {created}")
        print(f"  Stopped: {stopped}")
        print(f"  Status: {task['lastStatus']}")
        print(f"  Stopped Reason: {stopped_reason}")
        
        if task.get('containers'):
            container = task['containers'][0]
            exit_code = container.get('exitCode', 'N/A')
            reason = container.get('reason', 'N/A')
            print(f"  Container Exit Code: {exit_code}")
            if reason != 'N/A':
                print(f"  Container Reason: {reason}")
        
        # Check for failures
        if task.get('failures'):
            print(f"  FAILURES:")
            for failure in task['failures']:
                print(f"    - {failure.get('reason', 'Unknown')}")
                if failure.get('detail'):
                    print(f"      Detail: {failure['detail']}")
        
        print()
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("="*80)
print("COMMON FAILURE REASONS:")
print("="*80)
print("\n1. 'CannotPullContainerError' - Docker image not found or no permission")
print("2. 'ResourceInitializationError' - Can't pull image or mount volumes")
print("3. 'Essential container in task exited' - Container crashed")
print("4. Task stopped before starting - Usually networking or IAM issues")
