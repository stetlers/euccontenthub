"""
Check ECS task status and logs
"""
import boto3
from datetime import datetime

ecs_client = boto3.client('ecs', region_name='us-east-1')
logs_client = boto3.client('logs', region_name='us-east-1')

task_id = '46b9b4fa8fc648baa8ede2baef007a21'
task_arn = f'arn:aws:ecs:us-east-1:031421429609:task/selenium-crawler-cluster/{task_id}'

print("=" * 80)
print(f"ECS Task Status: {task_id}")
print("=" * 80)

# Check task status
try:
    tasks = ecs_client.describe_tasks(
        cluster='selenium-crawler-cluster',
        tasks=[task_arn]
    )
    
    if tasks['tasks']:
        task = tasks['tasks'][0]
        status = task['lastStatus']
        print(f"Status: {status}")
        
        if status == 'STOPPED':
            exit_code = task['containers'][0].get('exitCode', 'N/A')
            stop_reason = task.get('stoppedReason', 'N/A')
            print(f"Exit Code: {exit_code}")
            print(f"Stop Reason: {stop_reason}")
            
            if exit_code == 0:
                print("\n✅ Task completed successfully!")
            else:
                print(f"\n❌ Task failed!")
        elif status == 'RUNNING':
            print("\n⏳ Task is still running...")
        else:
            print(f"\n📊 Task status: {status}")
    else:
        print("Task not found")
        
except Exception as e:
    print(f"Error checking task: {e}")

# Check logs
print("\n" + "=" * 80)
print("Recent ECS Logs")
print("=" * 80)

try:
    # Get log stream
    log_group = '/ecs/selenium-crawler'
    log_stream = f'ecs/selenium-crawler/{task_id}'
    
    events = logs_client.get_log_events(
        logGroupName=log_group,
        logStreamName=log_stream,
        startFromHead=False,
        limit=30
    )
    
    if events['events']:
        for event in events['events'][-20:]:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            print(f"[{timestamp.strftime('%H:%M:%S')}] {event['message'].strip()}")
    else:
        print("No log events found")
        
except Exception as e:
    print(f"Could not fetch logs: {e}")
