import boto3
import json
import time

ecs_client = boto3.client('ecs', region_name='us-east-1')

# Test with the first Builder.AWS post
test_post_id = 'builder-building-a-simple-content-summarizer-with-amazon-bedrock'

print(f"Running ECS task for post: {test_post_id}")
print("=" * 80)

# Run the task
response = ecs_client.run_task(
    cluster='selenium-crawler-cluster',
    taskDefinition='selenium-crawler-task:3',
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
                        'value': 'aws-blog-posts-staging'
                    },
                    {
                        'name': 'ENVIRONMENT',
                        'value': 'staging'
                    }
                ]
            }
        ]
    }
)

if response['tasks']:
    task_arn = response['tasks'][0]['taskArn']
    task_id = task_arn.split('/')[-1]
    print(f"✓ Task started: {task_id}")
    print(f"✓ Full ARN: {task_arn}")
    print(f"\nMonitor logs at:")
    print(f"https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Fecs$252Fselenium-crawler")
    print(f"\nWaiting for task to complete (this may take 2-3 minutes)...")
    
    # Wait for task to complete
    waiter = ecs_client.get_waiter('tasks_stopped')
    try:
        waiter.wait(
            cluster='selenium-crawler-cluster',
            tasks=[task_arn],
            WaiterConfig={'Delay': 10, 'MaxAttempts': 30}
        )
        print("\n✓ Task completed!")
        
        # Get final task status
        tasks = ecs_client.describe_tasks(
            cluster='selenium-crawler-cluster',
            tasks=[task_arn]
        )
        
        if tasks['tasks']:
            task = tasks['tasks'][0]
            exit_code = task['containers'][0].get('exitCode', 'N/A')
            status = task['lastStatus']
            print(f"Status: {status}")
            print(f"Exit code: {exit_code}")
            
            if exit_code == 0:
                print("\n✅ SUCCESS! Check DynamoDB for updated author.")
            else:
                print(f"\n❌ Task failed with exit code {exit_code}")
                print("Check CloudWatch logs for details.")
    except Exception as e:
        print(f"\n⚠️ Timeout or error waiting for task: {e}")
        print("Task may still be running. Check CloudWatch logs.")
else:
    print("❌ Failed to start task")
    if response.get('failures'):
        print(f"Failures: {json.dumps(response['failures'], indent=2)}")
