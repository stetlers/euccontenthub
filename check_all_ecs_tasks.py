"""
Check all recent ECS tasks in the cluster
"""
import boto3
from datetime import datetime

ecs = boto3.client('ecs', region_name='us-east-1')

cluster_name = 'builder-crawler-cluster'

print("=" * 80)
print("Checking all ECS tasks in cluster")
print("=" * 80)

# List all tasks (running and stopped)
try:
    # Get running tasks
    running_response = ecs.list_tasks(
        cluster=cluster_name,
        desiredStatus='RUNNING'
    )
    
    # Get stopped tasks (recent)
    stopped_response = ecs.list_tasks(
        cluster=cluster_name,
        desiredStatus='STOPPED',
        maxResults=10
    )
    
    all_task_arns = running_response['taskArns'] + stopped_response['taskArns']
    
    if not all_task_arns:
        print("\nNo tasks found in cluster")
    else:
        # Get task details
        tasks_response = ecs.describe_tasks(
            cluster=cluster_name,
            tasks=all_task_arns
        )
        
        print(f"\nFound {len(tasks_response['tasks'])} tasks:\n")
        
        for task in sorted(tasks_response['tasks'], key=lambda x: x['createdAt'], reverse=True):
            task_id = task['taskArn'].split('/')[-1]
            status = task['lastStatus']
            created = task['createdAt'].strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"Task: {task_id}")
            print(f"  Status: {status}")
            print(f"  Created: {created}")
            
            if status == 'STOPPED':
                stopped_reason = task.get('stoppedReason', 'Unknown')
                stopped_at = task.get('stoppedAt')
                if stopped_at:
                    stopped_at = stopped_at.strftime('%Y-%m-%d %H:%M:%S')
                    print(f"  Stopped: {stopped_at}")
                print(f"  Reason: {stopped_reason}")
            
            print()

except Exception as e:
    print(f"\nError: {e}")
