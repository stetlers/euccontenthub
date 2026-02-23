import boto3
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')

print("=" * 60)
print("Detailed Sitemap Crawler Logs")
print("=" * 60)

log_group = '/aws/lambda/aws-blog-crawler'
start_time = int((datetime.now() - timedelta(minutes=10)).timestamp() * 1000)

try:
    response = logs_client.filter_log_events(
        logGroupName=log_group,
        startTime=start_time,
        filterPattern=''
    )
    
    print(f"\nTotal log events: {len(response['events'])}\n")
    
    # Print last 100 lines
    for event in response['events'][-100:]:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event['message'].strip()
        print(f"{timestamp.strftime('%H:%M:%S')} | {message}")
    
except Exception as e:
    print(f"Error: {e}")
