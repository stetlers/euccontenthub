"""Check CloudWatch logs for recent query processing"""
import boto3
from datetime import datetime

logs_client = boto3.client('logs', region_name='us-east-1')

FUNCTION_NAME = 'aws-blog-chat-assistant'
LOG_GROUP = f'/aws/lambda/{FUNCTION_NAME}'

print("Checking recent query logs...")
print("=" * 70)

try:
    # Get the most recent log stream
    response = logs_client.describe_log_streams(
        logGroupName=LOG_GROUP,
        orderBy='LastEventTime',
        descending=True,
        limit=1
    )
    
    if not response['logStreams']:
        print("No recent log streams found")
        exit(0)
    
    stream_name = response['logStreams'][0]['logStreamName']
    last_event = datetime.fromtimestamp(response['logStreams'][0]['lastEventTimestamp']/1000)
    
    print(f"Latest log stream: {stream_name}")
    print(f"Last event: {last_event}")
    print()
    
    # Get recent log events
    events_response = logs_client.get_log_events(
        logGroupName=LOG_GROUP,
        logStreamName=stream_name,
        limit=500,
        startFromHead=False
    )
    
    # Find the most recent query
    events = events_response['events']
    
    # Look for query-related logs
    print("Recent Query Processing:")
    print("-" * 70)
    
    found_query = False
    query_logs = []
    
    for event in reversed(events[-100:]):  # Check last 100 events
        message = event['message']
        
        # Look for query keywords
        if any(keyword in message for keyword in ['Query keywords:', 'User Query:', 'Event:', 'workspaces applications', 'appstream']):
            query_logs.append(message.strip())
            found_query = True
        
        # Also capture scoring and filtering logs
        if found_query and any(keyword in message for keyword in ['Filtered to', 'Retrieved', 'Top 5 scores', 'Detected domain']):
            query_logs.append(message.strip())
    
    if query_logs:
        for log in query_logs[-20:]:  # Show last 20 relevant logs
            print(log)
    else:
        print("No query processing logs found")
        print("\nShowing last 10 messages:")
        for event in events[-10:]:
            print(event['message'].strip())

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
