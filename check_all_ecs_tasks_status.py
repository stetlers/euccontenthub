"""
Check status of all recent ECS tasks
"""
import boto3
from datetime import datetime

ecs = boto3.client('ecs', region_name='us-east-1')

cluster_name = 'selenium-crawler-cluster'

print("=" * 80)
print("CHECKING ALL RECENT ECS TASKS")
print("=" * 80)

# List recent tasks
response = ecs.list_tasks(
    cluster=cluster_name,
    maxResults=10,
    desiredStatus='STOPPED'
)

task_arns = response['taskArns']

if not task_arns:
    print("\nNo recent stopped tasks found")
else:
    # Get task details
    tasks_response = ecs.describe_tasks(
        cluster=cluster_name,
        tasks=task_arns
    )
    
    print(f"\nFound {len(tasks_response['tasks'])} recent tasks:\n")
    
    for task in sorted(tasks_response['tasks'], key=lambda x: x['createdAt'], reverse=True):
        task_id = task['taskArn'].split('/')[-1]
        status = task['lastStatus']
        created = task['createdAt'].strftime('%Y-%m-%d %H:%M:%S')
        stopped = task.get('stoppedAt')
        stopped_str = stopped.strftime('%Y-%m-%d %H:%M:%S') if stopped else 'N/A'
        stopped_reason = task.get('stoppedReason', 'Unknown')
        
        print(f"Task ID: {task_id}")
        print(f"  Status: {status}")
        print(f"  Created: {created}")
        print(f"  Stopped: {stopped_str}")
        print(f"  Reason: {stopped_reason}")
        print()

# Check running tasks
running_response = ecs.list_tasks(
    cluster=cluster_name,
    desiredStatus='RUNNING'
)

running_arns = running_response['taskArns']

if running_arns:
    print("=" * 80)
    print(f"RUNNING TASKS: {len(running_arns)}")
    print("=" * 80)
    
    running_tasks = ecs.describe_tasks(
        cluster=cluster_name,
        tasks=running_arns
    )
    
    for task in running_tasks['tasks']:
        task_id = task['taskArn'].split('/')[-1]
        created = task['createdAt'].strftime('%Y-%m-%d %H:%M:%S')
        print(f"\nTask ID: {task_id}")
        print(f"  Status: RUNNING")
        print(f"  Created: {created}")
else:
    print("\n✅ No tasks currently running")
