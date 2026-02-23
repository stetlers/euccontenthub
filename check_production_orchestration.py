import boto3
import json

# Check Lambda aliases and ECS task status
lambda_client = boto3.client('lambda', region_name='us-east-1')
ecs_client = boto3.client('ecs', region_name='us-east-1')
logs_client = boto3.client('logs', region_name='us-east-1')

print("="*80)
print("CHECKING PRODUCTION ORCHESTRATION")
print("="*80)

# 1. Check crawler Lambda alias
print("\n1. Enhanced Crawler Lambda:")
try:
    response = lambda_client.get_alias(
        FunctionName='enhanced-crawler',
        Name='production'
    )
    print(f"   Alias: production → Version {response['FunctionVersion']}")
except Exception as e:
    print(f"   ERROR: {e}")

# 2. Check summary generator Lambda alias
print("\n2. Summary Generator Lambda:")
try:
    response = lambda_client.get_alias(
        FunctionName='aws-blog-summary-generator',
        Name='production'
    )
    print(f"   Alias: production → Version {response['FunctionVersion']}")
except Exception as e:
    print(f"   ERROR: {e}")

# 3. Check classifier Lambda alias
print("\n3. Classifier Lambda:")
try:
    response = lambda_client.get_alias(
        FunctionName='aws-blog-classifier',
        Name='production'
    )
    print(f"   Alias: production → Version {response['FunctionVersion']}")
except Exception as e:
    print(f"   ERROR: {e}")

# 4. Check recent ECS tasks
print("\n4. Recent ECS Tasks (last 10):")
try:
    response = ecs_client.list_tasks(
        cluster='selenium-crawler-cluster',
        maxResults=10,
        desiredStatus='STOPPED'
    )
    
    if response['taskArns']:
        tasks = ecs_client.describe_tasks(
            cluster='selenium-crawler-cluster',
            tasks=response['taskArns']
        )
        
        for task in tasks['tasks'][:5]:
            task_id = task['taskArn'].split('/')[-1]
            status = task['lastStatus']
            stopped_reason = task.get('stoppedReason', 'N/A')
            exit_code = 'N/A'
            
            # Get exit code from container
            if task.get('containers'):
                exit_code = task['containers'][0].get('exitCode', 'N/A')
            
            print(f"   Task: {task_id[:20]}... Status: {status}, Exit: {exit_code}")
            if stopped_reason and stopped_reason != 'Essential container in task exited':
                print(f"     Reason: {stopped_reason}")
    else:
        print("   No recent tasks found")
except Exception as e:
    print(f"   ERROR: {e}")

# 5. Check recent crawler logs
print("\n5. Recent Crawler Logs (last invocation):")
try:
    response = logs_client.filter_log_events(
        logGroupName='/aws/lambda/enhanced-crawler',
        limit=50
    )
    
    # Look for key messages
    for event in response['events'][-20:]:
        message = event['message'].strip()
        if any(keyword in message for keyword in ['Builder.AWS posts changed', 'Started ECS task', 'Failed to start']):
            print(f"   {message}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "="*80)
print("DIAGNOSIS:")
print("="*80)
print("Check if:")
print("1. ECS tasks are starting successfully")
print("2. ECS tasks are exiting with code 0 (success)")
print("3. Summary generator Lambda is being invoked")
print("4. Lambda aliases are pointing to correct versions")
