#!/usr/bin/env python3
"""
Manually test ECS task with a single post
"""
import boto3
import time

ecs_client = boto3.client('ecs', region_name='us-east-1')

print("="*80)
print("MANUALLY TESTING ECS TASK")
print("="*80)

# Use a single test post
test_post_id = 'builder-manage-your-entra-id-joined-amazon-workspaces-personal-settings'

print(f"\nStarting ECS task for test post: {test_post_id}")

try:
    response = ecs_client.run_task(
        cluster='selenium-crawler-cluster',
        taskDefinition='selenium-crawler-task',
        launchType='FARGATE',
        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets': ['subnet-b2a60bed'],
                'securityGroups': ['sg-06c921b4472e87b70'],
                'assignPublicIp': 'ENABLED'
            }
        },
        overrides={
            'containerOverrides': [
                {
                    'name': 'selenium-crawler',
                    'environment': [
                        {
                            'name': 'POST_IDS',
                            'value': test_post_id
                        },
                        {
                            'name': 'DYNAMODB_TABLE_NAME',
                            'value': 'aws-blog-posts'
                        },
                        {
                            'name': 'ENVIRONMENT',
                            'value': 'production'
                        }
                    ]
                }
            ]
        }
    )
    
    if response.get('tasks'):
        task = response['tasks'][0]
        task_arn = task['taskArn']
        task_id = task_arn.split('/')[-1]
        
        print(f"\n✓ Task started successfully!")
        print(f"  Task ID: {task_id}")
        print(f"  Task ARN: {task_arn}")
        print(f"  Status: {task['lastStatus']}")
        
        print(f"\nWaiting 10 seconds for task to start...")
        time.sleep(10)
        
        # Check task status
        print(f"\nChecking task status...")
        status_response = ecs_client.describe_tasks(
            cluster='selenium-crawler-cluster',
            tasks=[task_arn]
        )
        
        if status_response['tasks']:
            task = status_response['tasks'][0]
            print(f"  Status: {task['lastStatus']}")
            print(f"  Desired Status: {task['desiredStatus']}")
            
            if task.get('stoppedReason'):
                print(f"  Stopped Reason: {task['stoppedReason']}")
            
            if task.get('containers'):
                container = task['containers'][0]
                print(f"  Container Status: {container.get('lastStatus', 'Unknown')}")
                if container.get('reason'):
                    print(f"  Container Reason: {container['reason']}")
        
        print(f"\nTo check logs:")
        print(f"  aws logs tail /ecs/selenium-crawler --follow --log-stream-name ecs/selenium-crawler/{task_id}")
        
    else:
        print(f"\n✗ Failed to start task")
        if response.get('failures'):
            print(f"\nFailures:")
            for failure in response['failures']:
                print(f"  - {failure.get('reason', 'Unknown')}")
                if failure.get('detail'):
                    print(f"    Detail: {failure['detail']}")
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
