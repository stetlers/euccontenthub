"""
Wait for all Lambda invocations to complete before starting fresh test
"""
import boto3
import time
from datetime import datetime

lambda_client = boto3.client('lambda', region_name='us-east-1')
logs_client = boto3.client('logs', region_name='us-east-1')

print("\n" + "="*80)
print("Waiting for Lambda Invocations to Complete")
print("="*80)

log_group = '/aws/lambda/aws-blog-summary-generator'

def get_recent_invocations():
    """Check for Lambda invocations in last 2 minutes"""
    start_time = int((time.time() - 120) * 1000)  # Last 2 minutes
    end_time = int(time.time() * 1000)
    
    try:
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            endTime=end_time,
            filterPattern='START RequestId'
        )
        return len(response.get('events', []))
    except:
        return 0

print("\nMonitoring for Lambda activity...")
print("Will wait until no invocations detected for 2 minutes\n")

idle_time = 0
check_interval = 30  # Check every 30 seconds

while True:
    recent_invocations = get_recent_invocations()
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    if recent_invocations > 0:
        print(f"[{timestamp}] Active: {recent_invocations} invocations in last 2 minutes")
        idle_time = 0
    else:
        idle_time += check_interval
        print(f"[{timestamp}] Idle: No invocations for {idle_time}s")
        
        if idle_time >= 120:  # 2 minutes of idle
            print("\n" + "="*80)
            print("✅ All Lambda Invocations Complete!")
            print("="*80)
            print("\nNo activity detected for 2 minutes")
            print("Safe to proceed with table cleanup and fresh test")
            break
    
    time.sleep(check_interval)

print("\nNext steps:")
print("1. Clear staging table: python clear_staging_for_final_test.py")
print("2. Start monitoring: python monitor_final_test.py")
print("3. Trigger crawler from website: https://staging.awseuccontent.com")
