import boto3
from datetime import datetime, timedelta

lambda_client = boto3.client('lambda', region_name='us-east-1')
logs_client = boto3.client('logs', region_name='us-east-1')

print("=" * 60)
print("Lambda Function Status Check")
print("=" * 60)

# Check sitemap crawler
print("\n1. Sitemap Crawler (aws-blog-crawler)")
print("-" * 60)

try:
    # Get function configuration
    response = lambda_client.get_function(FunctionName='aws-blog-crawler')
    print(f"✓ Function exists")
    print(f"  Runtime: {response['Configuration']['Runtime']}")
    print(f"  Timeout: {response['Configuration']['Timeout']}s")
    print(f"  Last Modified: {response['Configuration']['LastModified']}")
    
    # Check recent invocations via CloudWatch
    log_group = '/aws/lambda/aws-blog-crawler'
    
    # Get log streams
    streams_response = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=5
    )
    
    print(f"\n  Recent log streams:")
    for stream in streams_response['logStreams']:
        last_event = datetime.fromtimestamp(stream['lastEventTimestamp'] / 1000)
        print(f"    - {stream['logStreamName']}")
        print(f"      Last event: {last_event.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get logs from most recent stream
    if streams_response['logStreams']:
        most_recent_stream = streams_response['logStreams'][0]['logStreamName']
        print(f"\n  Fetching logs from: {most_recent_stream}")
        
        events_response = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=most_recent_stream,
            limit=200,
            startFromHead=False  # Get most recent events
        )
        
        print(f"\n  Last 50 log lines:")
        print("  " + "-" * 56)
        for event in events_response['events'][-50:]:
            message = event['message'].strip()
            if message:  # Skip empty lines
                print(f"  {message}")
        
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "=" * 60)
